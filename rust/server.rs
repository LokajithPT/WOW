use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::env;

fn handle_client(mut stream: TcpStream) {
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut line = String::new();
    loop {
        line.clear();
        match reader.read_line(&mut line) {
            Ok(0) => break,
            Ok(_) => {
                let trimmed = line.trim();
                if let Some(seq) = trimmed.split(':').next() {
                    let ack = format!("ACK:{}\n", seq);
                    let _ = stream.write_all(ack.as_bytes());
                }
            }
            Err(_) => break,
        }
    }
}

fn main() {
    let port = env::args().nth(1).unwrap_or_else(|| "9876".to_string());
    let addr = format!("127.0.0.1:{}", port);
    let listener = TcpListener::bind(&addr).expect("Failed to bind");
    println!("READY:{}", port);
    if let Ok((stream, _)) = listener.accept() {
        stream.set_nodelay(true).ok();
        handle_client(stream);
    }
}
