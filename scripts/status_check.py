import asyncio
import time
import asyncio_mqtt as aiomqtt
from concurrent.futures import ProcessPoolExecutor


last_cycle: int = 0


async def check_last_cycle(client: aiomqtt.Client):
    global last_cycle
    while True:
        # if no data received in 10 minutes, send off topic
        if time.time() - last_cycle > 600:
            print('client is dead')
            await client.publish('box01/status', payload='OFF')
        else:
            print('client is alive')
            await client.publish('box01/status', payload='ON')
        
        await asyncio.sleep(60)


async def run(client: aiomqtt.Client):
    global last_cycle
    while True:
        try:
            async with client.messages() as messages:
                await client.subscribe("box01/temperature")
                async for message in messages:
                    print('received message')
                    last_cycle = time.time()
        except aiomqtt.MqttError:
            asyncio.sleep(5)

async def main():
    async with aiomqtt.Client("TOFILL") as client:
        await asyncio.gather(run(client), check_last_cycle(client))


if __name__ == '__main__':
    executor = ProcessPoolExecutor(2)
    asyncio.run(main())
