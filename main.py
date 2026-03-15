"""Simple Android chatbot app built with plain Kivy for stable APK builds."""

import json
import os
import threading
from typing import List

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup

MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT = (
    "You are a friendly, helpful AI assistant that supports multiple "
    "languages. Always reply in the same language as the user. "
    "Be clear, concise, and helpful."
)


def groq_chat(api_key: str, messages: List[dict]) -> str:
    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


KV = """
<KeyDialog>:
    orientation: "vertical"
    spacing: "10dp"
    padding: "14dp"
    TextInput:
        id: api_key_input
        multiline: False
        password: True
        hint_text: "Paste your Groq API key"
        text: root.current_key
        size_hint_y: None
        height: "44dp"
    BoxLayout:
        size_hint_y: None
        height: "44dp"
        spacing: "8dp"
        Button:
            text: "Cancel"
            on_release: root.close_dialog()
        Button:
            text: "Save"
            on_release: root.save_key(api_key_input.text)

BoxLayout:
    orientation: "vertical"
    padding: "10dp"
    spacing: "10dp"
    canvas.before:
        Color:
            rgba: 0.08, 0.09, 0.12, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: "48dp"
        spacing: "8dp"
        Button:
            text: "Set API Key"
            on_release: app.show_key_dialog()
        Button:
            text: "Clear Chat"
            on_release: app.clear_chat()

    ScrollView:
        do_scroll_x: False
        bar_width: "6dp"
        GridLayout:
            id: chat_box
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            spacing: "8dp"

    TextInput:
        id: chat_history
        readonly: True
        text: app.chat_text
        font_size: "15sp"
        foreground_color: 0.95, 0.96, 0.98, 1
        background_color: 0.14, 0.16, 0.2, 1
        size_hint_y: 0.55

    BoxLayout:
        size_hint_y: None
        height: "52dp"
        spacing: "8dp"
        TextInput:
            id: msg_field
            multiline: False
            hint_text: "Type a message"
            on_text_validate: app.send_message()
        Button:
            text: "Send"
            disabled: app.busy
            on_release: app.send_message()
"""


class KeyDialog(BoxLayout):
    def __init__(self, app_ref, current_key, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.current_key = current_key
        self.popup = None

    def save_key(self, key):
        key = (key or "").strip()
        if key:
            self.app_ref.api_key = key
            self.app_ref.save_api_key(key)
        self.close_dialog()

    def close_dialog(self):
        if self.popup:
            self.popup.dismiss()


class ChatBotApp(App):
    busy = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = ""
        self.history: List[dict] = []
        self.chat_text = "AI ChatBot\n\nSet API key and start chatting."

    def build(self):
        self.title = "AI ChatBot"
        return Builder.load_string(KV)

    def on_start(self):
        self.api_key = self.load_api_key()
        if not self.api_key:
            Clock.schedule_once(lambda dt: self.show_key_dialog(), 0.5)

    def config_path(self) -> str:
        return os.path.join(self.user_data_dir, "config.json")

    def load_api_key(self) -> str:
        try:
            path = self.config_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file_handle:
                    return json.load(file_handle).get("api_key", "")
        except Exception:
            pass
        return os.environ.get("GROQ_API_KEY", "")

    def save_api_key(self, key: str):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(self.config_path(), "w", encoding="utf-8") as file_handle:
                json.dump({"api_key": key}, file_handle)
        except Exception as exc:
            self.append_text("System", f"Could not save API key: {exc}")

    def show_key_dialog(self):
        dialog_content = KeyDialog(self, self.api_key)
        popup = Popup(
            title="Set Groq API Key",
            content=dialog_content,
            size_hint=(0.9, None),
            height="220dp",
            auto_dismiss=False,
        )
        dialog_content.popup = popup
        popup.open()

    def append_text(self, role: str, message: str):
        block = f"{role}:\n{message}\n\n"
        if self.chat_text.startswith("AI ChatBot\n\nSet API key"):
            self.chat_text = block
        else:
            self.chat_text += block
        if self.root:
            self.root.ids.chat_history.text = self.chat_text
            Clock.schedule_once(self.scroll_to_bottom, 0.1)

    def scroll_to_bottom(self, *_):
        if self.root:
            self.root.ids.chat_history.cursor = (0, len(self.root.ids.chat_history._lines))

    def send_message(self):
        if self.busy or not self.root:
            return

        text = self.root.ids.msg_field.text.strip()
        if not text:
            return
        if not self.api_key:
            self.show_key_dialog()
            return

        self.root.ids.msg_field.text = ""
        self.history.append({"role": "user", "content": text})
        self.append_text("You", text)
        self.append_text("Bot", "Thinking...")
        self.busy = True
        threading.Thread(target=self._api_thread, daemon=True).start()

    def _api_thread(self):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history
        try:
            reply = groq_chat(self.api_key, messages)
            self.history.append({"role": "assistant", "content": reply})
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else "?"
            reply = f"API error {status_code}. Check API key or rate limits."
        except requests.exceptions.ConnectionError:
            reply = "No internet connection."
        except requests.exceptions.Timeout:
            reply = "Request timed out."
        except Exception as exc:
            reply = f"Error: {exc}"

        Clock.schedule_once(lambda dt: self.finish_response(reply), 0)

    def finish_response(self, reply: str):
        if self.chat_text.endswith("Bot:\nThinking...\n\n"):
            self.chat_text = self.chat_text[: -len("Bot:\nThinking...\n\n")]
        self.append_text("Bot", reply)
        self.busy = False

    def clear_chat(self):
        self.history.clear()
        self.chat_text = "AI ChatBot\n\nSet API key and start chatting."
        if self.root:
            self.root.ids.chat_history.text = self.chat_text


if __name__ == "__main__":
    ChatBotApp().run()
