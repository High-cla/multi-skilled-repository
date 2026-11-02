// ============================================================
// Bounded localhost spawn server template.
// HTTP thread: validate + enqueue only. Main thread: spawn within a
// per-frame budget from OnUpdate/Update. Replace TrySpawnOne for the game.
// ============================================================
using System;
using System.Collections.Generic;
using System.Net;
using System.Text;
using System.Threading;
using System.Web;

public static class SpawnHttpServer
{
    private const string Prefix = "http://localhost:26880/";
    private const int MaxPendingRequests = 128;
    private const int MaxItemsPerUpdate = 4;
    private const int MaxCountPerRequest = 25;
    private const int MaxTrackedStatuses = 256;

    private sealed class SpawnJob
    {
        public string Id;
        public string ItemId;
        public int Requested;
        public int Spawned;
        public string State;
        public string Error;
    }

    private static readonly object LifecycleGate = new object();
    private static readonly object QueueGate = new object();
    private static readonly Queue<SpawnJob> Pending = new Queue<SpawnJob>();
    private static readonly Dictionary<string, SpawnJob> Statuses = new Dictionary<string, SpawnJob>();
    private static readonly Queue<string> StatusOrder = new Queue<string>();

    private static HttpListener _listener;
    private static Thread _serverThread;
    private static volatile bool _running;
    // Accessed only from the Unity/Melon main thread.
    private static SpawnJob _active;

    // Call from OnInitializeMelon() / plugin Awake().
    public static bool Start()
    {
        lock (LifecycleGate)
        {
            if (_running) return true;

            var listener = new HttpListener();
            listener.Prefixes.Add(Prefix);
            try
            {
                listener.Start();
                _listener = listener;
                _running = true;
                _serverThread = new Thread(() => ServerLoop(listener));
                _serverThread.IsBackground = true;
                _serverThread.Name = "SpawnHttpServer";
                _serverThread.Start();
                Console.WriteLine("[Spawn] listening on " + Prefix);
                return true;
            }
            catch (Exception ex)
            {
                _running = false;
                _listener = null;
                try { listener.Close(); } catch { }
                Console.WriteLine("[Spawn] start failed: " + ex.Message);
                return false;
            }
        }
    }

    // Call once per frame from OnUpdate()/Update(). At most
    // MaxItemsPerUpdate game objects are created during one frame.
    public static void DrainQueue()
    {
        for (int processed = 0; processed < MaxItemsPerUpdate; processed++)
        {
            SpawnJob job;
            lock (QueueGate)
            {
                if (_active == null)
                {
                    if (Pending.Count == 0) return;
                    _active = Pending.Dequeue();
                    _active.State = "processing";
                }
                job = _active;
            }

            string error;
            bool succeeded = TrySpawnOne(job.ItemId, out error);

            lock (QueueGate)
            {
                if (succeeded)
                {
                    job.Spawned++;
                    if (job.Spawned >= job.Requested)
                    {
                        job.State = "succeeded";
                        _active = null;
                    }
                }
                else
                {
                    job.Error = String.IsNullOrEmpty(error) ? "spawn failed" : error;
                    job.State = job.Spawned > 0 ? "partial" : "failed";
                    _active = null;
                }
                PruneStatusesLocked();
            }
        }
    }

    // Call from OnDeinitializeMelon() / plugin OnDestroy().
    public static void Stop()
    {
        HttpListener listener;
        Thread thread;
        lock (LifecycleGate)
        {
            _running = false;
            listener = _listener;
            thread = _serverThread;
            _listener = null;
            _serverThread = null;
        }

        try { if (listener != null) listener.Stop(); } catch { }
        try { if (listener != null) listener.Close(); } catch { }
        if (thread != null && thread != Thread.CurrentThread)
            try { thread.Join(1000); } catch { }

        lock (QueueGate)
        {
            while (Pending.Count > 0)
            {
                SpawnJob queued = Pending.Dequeue();
                queued.State = "failed";
                queued.Error = "server stopped before processing";
            }
            if (_active != null)
            {
                _active.State = _active.Spawned > 0 ? "partial" : "failed";
                _active.Error = "server stopped before request completed";
                _active = null;
            }
            PruneStatusesLocked();
        }
        Console.WriteLine("[Spawn] stopped");
    }

    private static void ServerLoop(HttpListener listener)
    {
        while (_running)
        {
            try
            {
                HttpListenerContext context = listener.GetContext();
                HandleRequest(context);
            }
            catch (HttpListenerException)
            {
                if (_running) Console.WriteLine("[Spawn] listener error");
                break;
            }
            catch (ObjectDisposedException) { break; }
            catch (Exception ex)
            {
                if (_running) Console.WriteLine("[Spawn] request loop: " + ex.Message);
            }
        }
    }

    private static void HandleRequest(HttpListenerContext context)
    {
        HttpListenerRequest request = context.Request;
        string path = request.Url == null ? "" : request.Url.AbsolutePath;
        if (request.HttpMethod == "OPTIONS")
        {
            WriteResponse(context.Response, 204, "");
            return;
        }
        if (request.HttpMethod != "GET")
        {
            WriteJson(context.Response, 405, "{\"ok\":false,\"err\":\"method not allowed\"}");
            return;
        }

        if (path == "/api/health")
        {
            int pending;
            lock (QueueGate) pending = Pending.Count;
            WriteJson(context.Response, 200,
                "{\"ok\":true,\"mode\":\"game\",\"pending\":" + pending +
                ",\"queueCapacity\":" + MaxPendingRequests + "}");
            return;
        }

        if (path == "/api/spawn")
        {
            var query = HttpUtility.ParseQueryString(request.Url.Query);
            string itemId = query["itemId"] ?? "";
            int count;
            if (String.IsNullOrWhiteSpace(itemId) || itemId.Length > 128 || HasControlChars(itemId))
            {
                WriteJson(context.Response, 400, "{\"ok\":false,\"state\":\"rejected\",\"err\":\"invalid itemId\"}");
                return;
            }
            if (!Int32.TryParse(query["count"] ?? "1", out count) || count < 1 || count > MaxCountPerRequest)
            {
                WriteJson(context.Response, 400,
                    "{\"ok\":false,\"state\":\"rejected\",\"err\":\"count must be 1-" + MaxCountPerRequest + "\"}");
                return;
            }

            SpawnJob job = Enqueue(itemId, count);
            if (job.State == "rejected")
            {
                WriteJson(context.Response, 429, JobJson(job));
                return;
            }
            // 202 means accepted into the bounded queue, not spawned in-game.
            WriteJson(context.Response, 202, JobJson(job));
            return;
        }

        if (path == "/api/spawn/status")
        {
            var query = HttpUtility.ParseQueryString(request.Url.Query);
            string id = query["id"] ?? "";
            SpawnJob job;
            string json;
            lock (QueueGate)
            {
                Statuses.TryGetValue(id, out job);
                json = job == null ? null : JobJson(job);
            }
            if (json == null)
                WriteJson(context.Response, 404, "{\"ok\":false,\"err\":\"unknown requestId\"}");
            else
                WriteJson(context.Response, 200, json);
            return;
        }

        WriteJson(context.Response, 404, "{\"ok\":false,\"err\":\"not found\"}");
    }

    private static SpawnJob Enqueue(string itemId, int count)
    {
        lock (QueueGate)
        {
            var job = new SpawnJob {
                Id = Guid.NewGuid().ToString("N"),
                ItemId = itemId,
                Requested = count,
                Spawned = 0,
                State = "received",
                Error = ""
            };
            Statuses[job.Id] = job;
            StatusOrder.Enqueue(job.Id);

            if (Pending.Count >= MaxPendingRequests)
            {
                job.State = "rejected";
                job.Error = "spawn queue is full";
            }
            else
            {
                Pending.Enqueue(job);
                job.State = "queued";
            }
            PruneStatusesLocked();
            return job;
        }
    }

    private static void PruneStatusesLocked()
    {
        int attempts = StatusOrder.Count;
        while (Statuses.Count > MaxTrackedStatuses && attempts-- > 0)
        {
            string oldId = StatusOrder.Dequeue();
            SpawnJob oldJob;
            if (!Statuses.TryGetValue(oldId, out oldJob)) continue;
            if (oldJob.State == "queued" || oldJob.State == "processing")
                StatusOrder.Enqueue(oldId);
            else
                Statuses.Remove(oldId);
        }
    }

    private static string JobJson(SpawnJob job)
    {
        lock (QueueGate)
        {
            return "{\"ok\":" + (job.State == "rejected" ? "false" : "true") +
                ",\"mode\":\"game\",\"requestId\":\"" + JsonEscape(job.Id) +
                "\",\"itemId\":\"" + JsonEscape(job.ItemId) +
                "\",\"state\":\"" + JsonEscape(job.State) +
                "\",\"requested\":" + job.Requested +
                ",\"spawned\":" + job.Spawned +
                ",\"err\":\"" + JsonEscape(job.Error) + "\"}";
        }
    }

    private static bool TrySpawnOne(string stableId, out string error)
    {
        try
        {
            // Replace this block with the game's main-thread API.
            // Example:
            // var inventory = YourInventoryProvider.MainInventory;
            // var item = DirectoryMaster.Item(stableId, true);
            // if (inventory == null || item == null) { error = "inventory/item unavailable"; return false; }
            // if (!inventory.MayHaveValidInventorySlot(item)) { error = "no valid inventory slot"; return false; }
            // if (!inventory.UncheckedAccept(item)) { error = "inventory rejected item"; return false; }
            // return true;
            error = "TrySpawnOne is a template placeholder; implement the game API before use";
            return false;
        }
        catch (Exception ex)
        {
            error = ex.Message;
            return false;
        }
    }

    private static bool HasControlChars(string value)
    {
        foreach (char c in value) if (Char.IsControl(c)) return true;
        return false;
    }

    private static string JsonEscape(string value)
    {
        if (value == null) return "";
        var result = new StringBuilder(value.Length + 8);
        foreach (char c in value)
        {
            switch (c)
            {
                case '"': result.Append("\\\""); break;
                case '\\': result.Append("\\\\"); break;
                case '\n': result.Append("\\n"); break;
                case '\r': result.Append("\\r"); break;
                case '\t': result.Append("\\t"); break;
                default:
                    if (c < 32) result.Append("\\u").Append(((int)c).ToString("x4"));
                    else result.Append(c);
                    break;
            }
        }
        return result.ToString();
    }

    private static void WriteJson(HttpListenerResponse response, int statusCode, string json)
    {
        WriteResponse(response, statusCode, json);
    }

    private static void WriteResponse(HttpListenerResponse response, int statusCode, string body)
    {
        try
        {
            byte[] bytes = Encoding.UTF8.GetBytes(body ?? "");
            response.StatusCode = statusCode;
            response.ContentType = "application/json; charset=utf-8";
            response.Headers["Access-Control-Allow-Origin"] = "*";
            response.Headers["Access-Control-Allow-Methods"] = "GET, OPTIONS";
            response.Headers["Access-Control-Allow-Headers"] = "Content-Type";
            response.ContentLength64 = bytes.Length;
            if (bytes.Length > 0) response.OutputStream.Write(bytes, 0, bytes.Length);
        }
        catch (Exception ex) { Console.WriteLine("[Spawn] response error: " + ex.Message); }
        finally { try { response.Close(); } catch { } }
    }
}
