import SwiftUI

func sendMQTT(topic: String, message: String){
    //Replace this IP address with your Raspberry Pi IP.
    guard let url = URL(string: "http://10.20.5.66:5000/send") else { return }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body = ["topic": topic, "message": message]
    request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    
    URLSession.shared.dataTask(with: request) { data, response, error in 
        if let error = error {
            print("Error sending MQTT message: \(error)")
        }else{
            print("Message sent to topic: \(topic)")
        }
    }.resume()
}

struct ContentView: View{
    @State private var lightOn = false
    @State private var fanOn = false
    @State private var doorOpen = false
    
    var body: some View {
        ZStack{
            Color.gray.ignoresSafeArea()
            
            VStack(spacing: 10) {
                Image(systemName: "house.fill")
                    .resizable()
                    .frame(width: 100, height: 100)
                    .foregroundColor(.white)
                    .padding(.bottom, 10)
                
                Text("Simpson's House")
                    .font(.title)
                    .foregroundColor(.white)
                
                Toggle(isOn: $lightOn) {
                    Label{
                        Text("Light")
                    } icon: {
                        Image(systemName: lightOn ? "lightbulb.fill" : "lightbulb")
                            .foregroundColor(lightOn ? .yellow : .gray)
                            .font(.title)
                    }
                }
                    .onChange(of: lightOn, initial: true){
                        oldValue, newValue in
                        let message = newValue ? "ON" : "OFF"
                        sendMQTT(topic: "light", message: message)
                    }
                    .toggleStyle(SwitchToggleStyle(tint: .yellow))
                    .padding()
                    .background(
                        .black.opacity(0.2))
                    .cornerRadius(10)
                    .foregroundColor(.white)
                    
                Toggle(isOn: $fanOn) {
                    Label{
                        Text("Fan")
                    } icon: {
                        Image(systemName: fanOn ? "fan.fill" : "fan")
                            .foregroundColor(fanOn ? .blue : .gray)
                            .font(.title)
                    }
                }
                    .onChange(of: fanOn, initial: true){
                        oldValue, newValue in
                        let message = newValue ? "ON" : "OFF"
                        sendMQTT(topic: "fan", message: message)
                    }
                    .toggleStyle(SwitchToggleStyle(tint: .blue))
                    .padding()
                    .background(
                        .black.opacity(0.2))
                    .cornerRadius(10)
                    .foregroundColor(.white)
                    
                Toggle(isOn: $doorOpen) {
                    Label{
                        Text("Door")
                    }icon: {
                        Image(systemName: doorOpen ? "door.left.hand.open" : "door.left.hand.closed")
                            .foregroundColor(doorOpen ? .brown : .gray)
                            .font(.title)
                    }
                }
                    .onChange(of: doorOpen, initial: true){
                        oldValue, newValue in
                        let message = newValue ? "ON" : "OFF"
                        sendMQTT(topic: "door", message: message)
                    }
                    .toggleStyle(SwitchToggleStyle(tint: .green))
                    .padding()
                    .background(
                        .black.opacity(0.2))
                    .cornerRadius(10)
                    .foregroundColor(.white)
                    
                }
                .padding(30)
            }
        }
    }

