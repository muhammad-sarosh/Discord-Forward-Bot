# **Discord Forward Bot**

A Python-based Discord bot that **forwards messages** from one channel to another while preserving formatting, attachments, timestamps, and author grouping.
It replicates Discord’s native display style, showing author names only for the first message in a block and skipping them for consecutive messages by the same user.

---

## **Features**

* Forward messages from one channel to another
* Re-upload attachments instead of linking them
* Preserves message order (**oldest → newest**)
* Toggles for:

  * Displaying author names
  * Showing timestamps in Discord-style format
* Groups consecutive messages by the same author (like Discord UI)
* Transfer full history or a **specific range** of messages using message links
* Skips oversized attachments gracefully and links them instead
* Automatically respects Discord API rate limits

---

## **Requirements**

* Python **3.9+**
* A Discord Bot Token ([Guide](https://discordpy.readthedocs.io/en/stable/discord.html))
* Required permissions for the bot:

  * **View Channels**
  * **Read Message History**
  * **Send Messages**
  * **Attach Files**
  * **Embed Links**
* **Important:**
  If you're forwarding messages **between two different servers**, the bot **must be invited to both servers** and must have the above permissions in **both the source and destination channels**.

---

## **Bot Setup**

Before running the bot, you need to create one in the **Discord Developer Portal** and configure it properly.

### **1. Create a New Bot**

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** → Enter a name → Click **Create**.
3. Go to the **Bot** tab in the sidebar.
4. Click **Add Bot** → Confirm by clicking **Yes, do it!**.

---

### **2. Get Your Bot Token**

1. Inside your application, go to the **Bot** tab.
2. Under the **Token** section, click **Reset Token** (if creating the bot for the first time).
3. Copy the **Bot Token** and paste it into your `keys.py` file:

   ```python
   BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
   ```

   > **Important:** Never share this token. If leaked, reset it immediately.

---

### **3. Set OAuth2 Permissions**

1. Go to the **OAuth2 → URL Generator** tab in your application.
2. Under **Scopes**, select:

   * `bot`
3. Scroll down to **Bot Permissions** and select:

   * **View Channels**
   * **Read Message History**
   * **Send Messages**
   * **Attach Files**
   * **Embed Links**
4. Copy the generated **invite link** from the bottom.
5. Paste it into your browser and invite the bot to:

   * **The source server** (where you’re fetching messages from)
   * **The destination server** (where you’re forwarding messages to)
6. Make sure the bot has the correct permissions in **both servers**.

---

## **Installation**

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/discord-forward-bot.git
   cd discord-forward-bot
   ```

2. **Install dependencies**:

   ```bash
   pip install -U discord.py
   ```

3. **Set up your bot token**:
   Open `keys.py` and add your Discord bot token:

   ```python
   BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
   ```

4. **Configure the bot**:
   Open `config.py` and set:

   * `SOURCE_CHANNEL_ID` → ID of the channel to read messages from.
   * `DEST_CHANNEL_ID` → ID of the channel to forward messages to.
   * Adjust formatting options, timestamp display, and transfer ranges as needed.

---

## **Configuration**

All primary settings are located in `config.py`.

| **Setting**               | **Type** | **Default** | **Description**                               |
| ------------------------- | -------- | ----------- | --------------------------------------------- |
| `SOURCE_CHANNEL_ID`       | int      | Required    | Channel to read messages from                 |
| `DEST_CHANNEL_ID`         | int      | Required    | Channel to send migrated messages to          |
| `SHOW_AUTHOR_NAME`        | bool     | `True`      | Whether to display author names               |
| `SHOW_TIMESTAMPS`         | bool     | `True`      | Whether to display timestamps                 |
| `START_MESSAGE_LINK`      | str      | `""`        | Start forwarding **after** this message       |
| `END_MESSAGE_LINK`        | str      | `""`        | Stop forwarding **at** this message           |
| `MAX_UPLOAD_BYTES`        | int      | `24MB`      | Max attachment size to re-upload              |
| `SLEEP_BETWEEN_SENDS_SEC` | float    | `0.35`      | Delay between messages to respect rate limits |

> **Tip**
> If both `START_MESSAGE_LINK` and `END_MESSAGE_LINK` are empty → forwards the **entire channel**.
> If only one is filled, forwards accordingly from or up to that message.

---

## **Usage**

Run the bot with:

```bash
python main.py
```

---

### **Example Scenarios**

#### **1. Forward Entire Channel**

Leave both `START_MESSAGE_LINK` and `END_MESSAGE_LINK` empty.

#### **2. Forward Specific Range**

Set:

```python
START_MESSAGE_LINK = "https://discord.com/channels/<guild>/<channel>/<start_message_id>"
END_MESSAGE_LINK   = "https://discord.com/channels/<guild>/<channel>/<end_message_id>"
```

#### **3. Forward From Start → Specific Message**

Leave `START_MESSAGE_LINK` empty and set `END_MESSAGE_LINK`.

#### **4. Forward From Message → End of Channel**

Leave `END_MESSAGE_LINK` empty and set `START_MESSAGE_LINK`.

---

## **Output Formatting**

The bot replicates Discord’s style:

* **Author grouping**
  Author names are shown **only** for the first message in a consecutive block.
* **Timestamps**
  Added next to the author name if enabled.
* **Attachments**
  Re-uploaded when possible; oversized files are replaced with links.

Example (author + timestamps enabled):

```
**John Doe** • *12/07/2025 3:06 PM*
First message.

Second message.

**Jane Smith** • *12/07/2025 3:08 PM*
Reply from Jane.
```

---

## **Known Limitations**

* Discord’s per-file upload limit applies (default: \~25 MB).
* Discord’s per-message file cap is 10 attachments; the bot automatically splits them into batches.
* Only supports **text channels** and **threads**.
* When forwarding between **two servers**, the bot **must** be added to both servers with the proper permissions.

---