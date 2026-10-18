import aiohttp
import asyncio
import json

url = "http://localhost:8000"

login= "/api/login"
me = "/api/users/me"

async def main():

    login_dict = {
        "grant_type": "password",
        "username": "test_user1",
        "password": "Test.Test01"
    }

    async with aiohttp.ClientSession() as session:
        # json = body
        # params = parameters
        # headers = headers
        # all accept dictionaries
        async with session.post(f"{url}{login}", data=login_dict, headers={'Content-Type': 'application/x-www-form-urlencoded'}) as resp:
            try:
                resp.raise_for_status()
            except Exception as e:
                raise Exception(resp.status, await resp.text())

            # .json()
            # .text()
            # ?? .content.iter_any()
            # toate cu await ca s async
            resp_json = await resp.json()

            print(json.dumps(resp_json, indent=4))
            return resp_json

async def cumvreitu(token):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{url}{me}", headers={'Authorization': f"Bearer {token}"}) as resp:
            try:
                resp.raise_for_status()
            except Exception as e:
                raise Exception(resp.status, await resp.text())

            resp_json = await resp.json()

            print(json.dumps(resp_json, indent=4))
            return resp_json

if __name__ == "__main__":
    resp = asyncio.run(main())
    asyncio.run(cumvreitu(resp.get("access_token")))