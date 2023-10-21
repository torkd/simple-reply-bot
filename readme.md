# simple-reply-bot

> Available on [DockerHub](https://hub.docker.com/r/torkd/simple-reply-bot)

A Telegram bot to answer messages with predetermined responses.\
The answers are defined in the config.json file, and support the response to be triggered by either a normal user or an admin. For ease of use, the docker compose will mount a local directory with such file. The config file can be reloaded at any time with the `/reload` command.\
More responses can be added either via the `/addcommand` bot command in a private chat with the bot or by editing the config file. To be able to use `/addcommand`you need to first `/claim` the bot in a private chat with it, or provide your Telegram ID as an environment variable in the compose file.\
**Be sure to use a compose file, you can find an example at the bottom.**

## Installation
- Create a `compose.yaml` file in the desired directory. (Example at the bottom of this page.)
	- Provide your local mounting point (be sure Docker will have proper read/write permissions for that directory).
	- Provide your Telegram Bot Token in the `compose.yaml` file as an environment variable
	- **_Optional_** Provide your Telegram ID in the `compose.yaml` file as an environment variable. This will give you ownership of the bot.
- Put your `config.json` file in your local mounting point. (Example at the bottom of this page.)
- Start the container with `docker compose up -d` (`-d` option for `detached` mode; the container will run in the background).

## Commands
Commands with a checkmark in the `Owner` or `Admin` columns require you to be either an admin or the owner.\
Commands with a checkmark in the `Private` *only* work in a private chat with the bot.

|               | Owner              | Admin              | Private            | Notes                                                                                                                                                                                                                                                     |
|---------------|--------------------|--------------------|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `/addadmin`   | :heavy_check_mark: | :x:                | :x:                | Gives a user admin privileges for the bot. If used in private the bot will ask to forward a message from the user to be added as an admin; if used in a group the command will need to be used in reply to a message of the user to be added as an admin. |
| `/deladmin`   | :heavy_check_mark: | :x:                | :heavy_check_mark: | Removes admin privileges from a user. Provides a list of current admins through an Inline Keyboard.                                                                                                                                                       |
| `/reload`     | :heavy_check_mark: | :x:                | :heavy_check_mark: | Reloads the `config.json` file.                                                                                                                                                                                                                           |
| `/addcommand` | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | Starts the process of adding a new command via chat. An optional parameter `reset` can be sent along (`/addcommand reset`) to reset the process.                                                                                                          |
| `/delcommand` | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | Deletes an existing command. Provides a list of commands through an Inline Keyboard.                                                                                                                                                                      |
| `/claim`      | :x:                | :x:                | :heavy_check_mark: | Provides ownership of the bot to the first user using the command. Can only be used once, and only if no `OWNER_ID` has been provided in the `compose.yaml` file.                                                                                         |
| `/start`      | :x:                | :x:                | :heavy_check_mark: | Replies with a standard greeting and a link to this documentation.                                                                                                                                                                                        |


## Config (config.json)
This is a base config file.\
Responses in the `admin` section will only be sent if the command is triggered by an admin.\
Responses in the `user` section will be triggered by anyone.\
Just add more commands as you please by adding to the JSON dictionary. The key will be the `/command` the bot will respond to, the value will be the actual response.\
Responses **must** abide by [Telegram Markdown V2 Style](https://core.telegram.org/bots/api#markdownv2-style) rules if added manually to this file, or they won't work.

```json
    {
        "admin": {
            "example1": "example 1"
        },
        "user": {
            "example2": "example 2"
        }
    }
```

## Docker compose (compose.yaml)
This is an example of the docker compose file you can use to run the bot.\
Make sure to put your `config.json` in the mounted directory, or the container will not start.\
If you wish to provide the `OWNER_ID`, make sure to remove the comment.

```yaml
    services:
    bot:
        image: "torkd/simple-reply-bot"
        volumes: 
        - ./config/:/bot/config/
        environment:
        BOT_TOKEN: <BOT_TOKEN>
        #OPTIONAL OWNER_ID: <OWNER_ID>
```
