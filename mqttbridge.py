from flask import Flask, request, jsonify
import paho.mqtt.publish as publish

app = Flask(__name__)

@app.route('/send', methods=['POST'])
def send():
    try:
        data = request.get_json()
        topic = data.get("topic")
        message = data.get("message")

        if not topic or not message:
            return jsonify({"error": "Missing topic or message"}), 400

        publish.single(topic, message, hostname="localhost")
        return jsonify({"status": "Message published"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Using host="0.0.0.0" exposes the service on all network interfaces,
    # not only the Pi's specific IP address
    app.run(host="0.0.0.0", port=5000)
