import asyncio
from sonar import SonarAgent

if __name__ == "__main__":
    asyncio.run(SonarAgent().chat_loop())