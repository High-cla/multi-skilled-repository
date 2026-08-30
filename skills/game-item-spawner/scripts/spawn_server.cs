// ============================================================
// 物品生成器: HTTP 服务器骨架 (游戏无关部分, 原样复用)
// 替换 TODO 标记的游戏专属部分 (步骤1逆向后填)
// 用法: 抄进你的 MelonLoader/BepInEx mod, 挂到主类
// 黄金法则: HTTP线程只入队, 主线程OnUpdate消费 (避免跨线程调游戏API)
// ============================================================
using System;
using System.Collections.Concurrent;
using System.Net;
using System.Text;
using System.Threading;
using System.Web;

// ---------- 游戏专属: 需替换的 3 处 ----------
// 1. SpawnItem 里: 如何创建物品 = 步骤1逆向结果 (如 DirectoryMaster.Item)
// 2. SpawnItem 里: 主背包获取 = 步骤1逆向结果 (如 EmporiumEntry.Instance.invElement)
// 3. SpawnItem 里: 入包 API = 步骤1逆向结果 (如 UncheckedAccept)

public static class SpawnHttpServer
{
    // ====== 配置 ======
    private const string PREFIX = "http://localhost:26880/";

    private static readonly ConcurrentQueue<(string itemId, int count)> Pending =
        new ConcurrentQueue<(string, int)>();
    private static HttpListener _listener;

    // 入口1: 模组 OnInitializeMelon 时调用
    public static void Start()
    {
        try
        {
            _listener = new HttpListener();
            _listener.Prefixes.Add(PREFIX);
            _listener.Start();
            var t = new Thread(ServerLoop) { IsBackground = true };
            t.Start();
            Console.WriteLine($"[Spawn] HTTP server on {PREFIX}");
        }
        catch (Exception e) { Console.WriteLine($"[Spawn] start ex: {e.Message}"); }
    }

    // 入口2: 模组 OnUpdate (主线程) 每次调用 — 消费队列
    public static void DrainQueue()
    {
        while (Pending.TryDequeue(out var job))
            SpawnItem(job.itemId, job.count);
    }

    // ====== 游戏专属: 唯一需要替换的方法 ======
    private static void SpawnItem(string stableId, int count)
    {
        try
        {
            // ====== TODO: 替换为步骤1逆向的游戏 API ======
            // 示例 (Probably Stolen):
            //   var inv = EmporiumEntry.Instance.invElement;
            //   if (inv == null) return;
            //   for (int i = 0; i < count; i++) {
            //       GameItem item = DirectoryMaster.Item(stableId, true);
            //       if (item == null) break;
            //       if (!((GameInventory)inv).MayHaveValidInventorySlot(item)) break;
            //       if (!((GameInventory)inv).UncheckedAccept(item)) break;
            //   }
            Console.WriteLine($"[Spawn] {count} x {stableId} (replace with game API)");
            // ====== TODO END ======
        }
        catch (Exception e) { Console.WriteLine($"[Spawn] ex: {e.Message}"); }
    }

    // ====== 以下为游戏无关 HTTP 引擎, 不用改 ======
    private static void ServerLoop()
    {
        while (_listener != null)
        {
            try
            {
                var ctx = _listener.GetContext();
                HandleRequest(ctx);
            }
            catch { /* listener stopped */ }
        }
    }

    private static void HandleRequest(HttpListenerContext ctx)
    {
        try
        {
            var req = ctx.Request;
            var res = ctx.Response;
            string body = "{\"ok\":false,\"err\":\"bad\"}";
            int code = 400;
            try
            {
                if (req.Url.AbsolutePath == "/api/spawn")
                {
                    var q = System.Web.HttpUtility.ParseQueryString(req.Url.Query);
                    string id = q["itemId"] ?? "";
                    int n = 1;
                    int.TryParse(q["count"], out n);
                    if (n < 1) n = 1;
                    if (id == "")
                        body = "{\"ok\":false,\"err\":\"no itemId\"}";
                    else
                    {
                        Pending.Enqueue((id, n));
                        body = $"{{\"ok\":true,\"queued\":\"{id} x{n}\"}}";
                        code = 200;
                    }
                }
                else if (req.Url.AbsolutePath == "/api/health")
                {
                    body = "{\"ok\":true}";
                    code = 200;
                }
            }
            catch (Exception e) { body = $"{{\"ok\":false,\"err\":\"{e.Message}\"}}"; code = 500; }
            byte[] buf = Encoding.UTF8.GetBytes(body);
            res.StatusCode = code;
            res.ContentType = "application/json; charset=utf-8";
            res.Headers["Access-Control-Allow-Origin"] = "*";   // 必须: 网页跨域fetch
            res.ContentLength64 = buf.Length;
            res.OutputStream.Write(buf, 0, buf.Length);
            res.OutputStream.Close();
        }
        catch { }
    }
}
