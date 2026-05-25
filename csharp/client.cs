using System.Net.Sockets;
using System.Diagnostics;

var addr = args[0];
var intervalMs = int.Parse(args[1]);
var count = args.Length > 2 ? int.Parse(args[2]) : 1000;

var parts = addr.Split(':');
var client = new TcpClient();
client.NoDelay = true;
client.Connect(parts[0], int.Parse(parts[1]));
client.ReceiveTimeout = 5000;
var stream = client.GetStream();
var reader = new StreamReader(stream);
var writer = new StreamWriter(stream) { AutoFlush = true };

for (int seq = 1; seq <= count; seq++)
{
    var sw = Stopwatch.StartNew();
    await writer.WriteLineAsync($"{seq}:{seq}");
    var response = await reader.ReadLineAsync();
    sw.Stop();

    Console.WriteLine($"SEQ:{seq}:{sw.Elapsed.TotalNanoseconds:F0}");

    if (seq < count)
        await Task.Delay(intervalMs);
}

Console.WriteLine("DONE");
