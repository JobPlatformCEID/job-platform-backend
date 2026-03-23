from channels.testing import WebsocketCommunicator
from django.test import TestCase
from core.asgi import application

class WebSocketTest(TestCase):
    async def test_connect(self):
        communicator = WebsocketCommunicator(application, "/ws/calls/testroom/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_send_receive(self):
        communicator = WebsocketCommunicator(application, "/ws/calls/testroom/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({"message": "hello"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["message"], "hello")

        await communicator.disconnect()