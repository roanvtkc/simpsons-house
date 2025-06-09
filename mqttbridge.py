from flask import Flask, request, jsonify
import paho.mqtt.publish as publish

app = Flask(__name__)

@app.route('/send', methods=['POST'])
def send():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        topic = data.get("topic")
        message = data.get("message")

        if not topic or not message:
            return jsonify({"error": "Missing topic or message"}), 400

        publish.single(topic, message, hostname="localhost")
        return jsonify({"status": "Message published"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Make server accessible on your Pi's local IP
    app.run(host="0.0.0.0", port=5000)
