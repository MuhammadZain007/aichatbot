"""
AI ChatBot - Android App
Powered by Groq API (Llama 3.3 70B) — FREE
"""

import json
import os
import threading
from typing import List, Optional

import requests
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT = (
    "You are a friendly, helpful AI assistant that supports multiple "
    "languages. Always reply in the SAME language the user is writing in. "
    "Be clear, concise, and helpful."
)


# ─────────────────────────────────────────────────────────────────────────────
# Groq API helper
# ─────────────────────────────────────────────────────────────────────────────
def groq_chat(api_key: str, messages: List[dict]) -> str:
    resp = requests.post(
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
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ─────────────────────────────────────────────────────────────────────────────
# KV Layout
# ─────────────────────────────────────────────────────────────────────────────
KV = """
MDScreen:
    md_bg_color: app.theme_cls.backgroundColor

    MDBoxLayout:
        orientation: "vertical"

        # ── Top App Bar ───────────────────────────────────────────────────
        MDTopAppBar:
            title: "AI ChatBot"
            elevation: 2
            right_action_items:
                [
                    ["key-variant", lambda x: app.show_key_dialog(),
                     "Set API Key"],
                    ["broom", lambda x: app.clear_chat(),
                     "Clear Chat"]
                ]

        # ── Messages scrollable area ──────────────────────────────────────
        ScrollView:
            id: sv
            do_scroll_x: False

            MDBoxLayout:
                id: chat_box
                orientation: "vertical"
                padding: dp(10), dp(10)
                spacing: dp(8)
                size_hint_y: None
                height: self.minimum_height

        # ── Input row ─────────────────────────────────────────────────────
        MDBoxLayout:
            orientation: "horizontal"
            padding: dp(8), dp(6)
            spacing: dp(6)
            size_hint_y: None
            height: dp(68)
            md_bg_color: app.theme_cls.surfaceColor

            MDTextField:
                id: msg_field
                hint_text: "Type a message…"
                mode: "outlined"
                multiline: False
                on_text_validate: app.send_message()
                size_hint_x: 1

            MDIconButton:
                icon: "send"
                theme_icon_color: "Custom"
                icon_color: app.theme_cls.primaryColor
                on_release: app.send_message()
"""


# ─────────────────────────────────────────────────────────────────────────────
# Chat Bubble widget
# ─────────────────────────────────────────────────────────────────────────────
class ChatBubble(BoxLayout):
    """
    A chat message bubble.
    User messages are right-aligned (blue), bot messages left-aligned (dark).
    """

    def __init__(self, text: str, is_user: bool = True, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            **kwargs,
        )

        # ── Label ────────────────────────────────────────────────────────
        self._label = MDLabel(
            text=text,
            adaptive_height=True,
            size_hint_x=None,
            width=dp(250),
            theme_text_color="Custom",
            text_color=[1, 1, 1, 1] if is_user else [0.92, 0.92, 0.92, 1],
            padding=[dp(12), dp(8)],
        )

        # ── Card (background bubble) ──────────────────────────────────────
        self._card = MDCard(
            size_hint=(None, None),
            width=dp(270),
            radius=[dp(16), dp(16),
                    dp(4) if is_user else dp(16),
                    dp(16) if is_user else dp(4)],
            elevation=1,
            md_bg_color=(
                [0.18, 0.47, 0.95, 1] if is_user else [0.22, 0.22, 0.27, 1]
            ),
        )
        self._card.add_widget(self._label)

        # Height sync: card follows label, bubble follows card
        self._label.bind(height=self._sync_height)
        Clock.schedule_once(lambda dt: self._sync_height(self._label, self._label.height), 0.1)

        spacer = Widget(size_hint_x=1)

        if is_user:
            self.add_widget(spacer)
            self.add_widget(self._card)
        else:
            self.add_widget(self._card)
            self.add_widget(spacer)

    def _sync_height(self, instance, value):
        self._card.height = value + dp(4)
        self.height = self._card.height + dp(6)

    def set_text(self, text: str):
        """Dynamically update the bubble text (used for loading → reply)."""
        self._label.text = text


# ─────────────────────────────────────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────────────────────────────────────
class ChatBotApp(MDApp):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key: str = ""
        self.history: List[dict] = []
        self.busy: bool = False
        self._loading_bubble: Optional[ChatBubble] = None
        self._key_dialog: Optional[MDDialog] = None
        self._key_field: Optional[MDTextField] = None

    # ── Build ─────────────────────────────────────────────────────────────
    def build(self):
        self.title = "AI ChatBot"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        return Builder.load_string(KV)

    def on_start(self):
        # Load saved API key from app's private storage
        self.api_key = self._load_api_key()
        if not self.api_key:
            Clock.schedule_once(lambda dt: self.show_key_dialog(), 0.8)

    # ── Config persistence ────────────────────────────────────────────────
    def _config_path(self) -> str:
        return os.path.join(self.user_data_dir, "config.json")

    def _load_api_key(self) -> str:
        try:
            path = self._config_path()
            if os.path.exists(path):
                return json.loads(open(path).read()).get("api_key", "")
        except Exception:
            pass
        # Fallback: check environment variable (development use)
        return os.environ.get("GROQ_API_KEY", "")

    def _save_api_key(self, key: str):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(self._config_path(), "w") as f:
                json.dump({"api_key": key}, f)
        except Exception as e:
            print(f"Could not save config: {e}")

    # ── API Key Dialog ────────────────────────────────────────────────────
    def show_key_dialog(self):
        self._key_field = MDTextField(
            hint_text="Paste your Groq API key",
            text=self.api_key,
            password=True,
            mode="outlined",
            size_hint_x=1,
        )
        self._key_dialog = MDDialog(
            title="Set Groq API Key",
            type="custom",
            content_cls=self._key_field,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: self._key_dialog.dismiss(),
                ),
                MDRaisedButton(
                    text="SAVE",
                    on_release=self._apply_key,
                ),
            ],
        )
        self._key_dialog.open()

    def _apply_key(self, *_):
        key = (self._key_field.text or "").strip()
        if key:
            self.api_key = key
            self._save_api_key(key)
        self._key_dialog.dismiss()

    # ── Send Message ──────────────────────────────────────────────────────
    def send_message(self):
        if self.busy:
            return

        field = self.root.ids.msg_field
        text = field.text.strip()

        if not text:
            return

        if not self.api_key:
            self.show_key_dialog()
            return

        field.text = ""
        self.history.append({"role": "user", "content": text})
        self._add_bubble(text, is_user=True)

        # Show animated loading placeholder
        self._loading_bubble = self._add_bubble("Thinking…", is_user=False)
        self.busy = True

        threading.Thread(target=self._api_thread, daemon=True).start()

    # ── Background API Call ───────────────────────────────────────────────
    def _api_thread(self):
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history
        reply = ""
        try:
            reply = groq_chat(self.api_key, msgs)
            self.history.append({"role": "assistant", "content": reply})
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else "?"
            reply = f"⚠ API Error {code} — check your API key."
        except requests.exceptions.ConnectionError:
            reply = "⚠ No internet connection."
        except requests.exceptions.Timeout:
            reply = "⚠ Request timed out. Please try again."
        except Exception as e:
            reply = f"⚠ Error: {e}"
        finally:
            self.busy = False

        Clock.schedule_once(lambda dt: self._finish_response(reply), 0)

    def _finish_response(self, reply: str):
        box = self.root.ids.chat_box
        if self._loading_bubble and self._loading_bubble.parent:
            box.remove_widget(self._loading_bubble)
        self._loading_bubble = None
        self._add_bubble(reply, is_user=False)

    # ── Helpers ───────────────────────────────────────────────────────────
    def _add_bubble(self, text: str, is_user: bool) -> ChatBubble:
        bubble = ChatBubble(text=text, is_user=is_user)
        self.root.ids.chat_box.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.root.ids.sv, "scroll_y", 0), 0.2)
        return bubble

    def clear_chat(self):
        self.history.clear()
        self._loading_bubble = None
        self.root.ids.chat_box.clear_widgets()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ChatBotApp().run()
