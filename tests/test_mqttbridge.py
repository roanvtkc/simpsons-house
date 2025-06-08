import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import mqttbridge
import pytest

@pytest.fixture
def client():
    mqttbridge.app.config['TESTING'] = True
    with mqttbridge.app.test_client() as client:
        yield client

def test_send_valid_payload(mocker, client):
    mock_publish = mocker.patch('mqttbridge.publish.single')
    resp = client.post('/send', json={'topic': 'test', 'message': 'hello'})
    assert resp.status_code == 200
    assert resp.get_json() == {'status': 'Message published'}
    mock_publish.assert_called_once_with('test', 'hello', hostname='localhost')

def test_send_missing_fields(client):
    resp = client.post('/send', json={'topic': 'test'})
    assert resp.status_code == 400
    assert resp.get_json() == {'error': 'Missing topic or message'}

def test_send_invalid_json(client):
    resp = client.post('/send', data='not json', content_type='text/plain')
    assert resp.status_code == 400
    assert resp.get_json() == {'error': 'Invalid JSON payload'}
