using System.Net;
using System.Net.Sockets;

var port = args.Length > 0 ? args[0] : "9876";
var listener = new TcpListener(IPAddress.Loopback, int.Parse(port));
listener.Start();
Console.WriteLine($"READY:{port}");

var client = await listener.AcceptTcpClientAsync();
client.NoDelay = true;
client.ReceiveTimeout = 5000;
var stream = client.GetStream();
var reader = new StreamReader(stream);
var writer = new StreamWriter(stream) { AutoFlush = true };

while (true)
{
    var line = await reader.ReadLineAsync();
    if (line == null) break;
    var seq = line.Split(':')[0];
    await writer.WriteLineAsync($"ACK:{seq}");
}
