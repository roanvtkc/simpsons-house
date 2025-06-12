import SwiftUI

func sendMQTT(topic: String, message: String) {
    guard let url = URL(string: "http://10.20.5.66:5000/send") else { return }
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    let body = ["topic": topic, "message": message]
    request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    
    URLSession.shared.dataTask(with: request) { _, _, error in
        if let error = error {
            print("Error sending MQTT message: \(error)")
        } else {
            print("Message sent to topic: \(topic)")
        }
    }.resume()
}

struct ContentView: View {
    @State private var lightOn   = false
    @State private var fanOn     = false
    @State private var doorOpen  = false
    
    var body: some View {
        ZStack {
            Color.gray.ignoresSafeArea()
            VStack(spacing: 20) {
                Image(systemName: "house.fill")
                    .resizable()
                    .frame(width: 100, height: 100)
                    .foregroundColor(.white)
                
                Text("Simpson's House")
                    .font(.title)
                    .foregroundColor(.white)
                
                // Light toggle
                Toggle(isOn: $lightOn) {
                    Label("Light", systemImage: lightOn ? "lightbulb.fill" : "lightbulb")
                        .font(.title2)
                }
                .toggleStyle(SwitchToggleStyle(tint: .yellow))
                .padding()
                .background(Color.black.opacity(0.2))
                .cornerRadius(10)
                .onChange(of: lightOn) { oldValue, newValue in
                    sendMQTT(topic: "light", message: newValue ? "ON" : "OFF")
                }
                
                // Fan toggle
                Toggle(isOn: $fanOn) {
                    Label("Fan", systemImage: fanOn ? "fan.fill" : "fan")
                        .font(.title2)
                }
                .toggleStyle(SwitchToggleStyle(tint: .blue))
                .padding()
                .background(Color.black.opacity(0.2))
                .cornerRadius(10)
                .onChange(of: fanOn) { oldValue, newValue in
                    sendMQTT(topic: "fan", message: newValue ? "ON" : "OFF")
                }
                
                // Door toggle
                Toggle(isOn: $doorOpen) {
                    Label("Door", systemImage: doorOpen ? "door.left.hand.open" : "door.left.hand.closed")
                        .font(.title2)
                }
                .toggleStyle(SwitchToggleStyle(tint: .green))
                .padding()
                .background(Color.black.opacity(0.2))
                .cornerRadius(10)
                .onChange(of: doorOpen) { oldValue, newValue in
                    sendMQTT(topic: "door", message: newValue ? "ON" : "OFF")
                }
            }
            .padding(30)
        }
    }
}
