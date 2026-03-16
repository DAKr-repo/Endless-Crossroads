"""
codex.stubs.discord_stub — Comprehensive offline discord.py SDK
================================================================

Mirrors the discord.py (py-cord fork) API surface used by codex/bots/discord_bot.py.
Provides real state tracking (Embeds store fields, VoiceClients track connection, etc.)
so tests and offline tools can import discord_bot without the real library.

Sections match discord.py module layout:
  A. Core Types          F. Opus
  B. Enums               G. Sinks
  C. Embed System        H. Commands (ext.commands)
  D. UI Components       I. Tasks (ext.tasks)
  E. Voice               J. App Commands
                          K. install()
"""

import sys
import types

# ═══════════════════════════════════════════════════════════════════════════════
# A. CORE TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class InteractionResponse:
    """Mimics discord.InteractionResponse with double-response guard."""

    def __init__(self):
        self._responded = False

    async def send_message(self, content="", *, embed=None, view=None,
                           ephemeral=False):
        if self._responded:
            raise RuntimeError("This interaction has already been responded to.")
        self._responded = True

    async def defer(self, *, ephemeral=False):
        if self._responded:
            raise RuntimeError("This interaction has already been responded to.")
        self._responded = True

    @property
    def is_done(self):
        return self._responded


class InteractionFollowup:
    """Mimics discord.Interaction.followup."""

    async def send(self, content="", *, embed=None, view=None, ephemeral=False):
        pass


class Interaction:
    """Mimics discord.Interaction."""

    def __init__(self):
        self.response = InteractionResponse()
        self.followup = InteractionFollowup()
        self.channel = None
        self.data = {"values": []}
        self.user = None
        self.guild = None


class Intents:
    """Mimics discord.Intents with default() classmethod."""

    def __init__(self):
        self.message_content = True
        self.members = True
        self.voice_states = True
        self.guilds = True

    @classmethod
    def default(cls):
        return cls()


class File:
    """Mimics discord.File."""

    def __init__(self, fp=None, *, filename=None):
        self.fp = fp
        self.filename = filename


class Activity:
    """Mimics discord.Activity."""

    def __init__(self, *, type=None, name=""):
        self.type = type
        self.name = name


class Object:
    """Mimics discord.Object."""

    def __init__(self, id=0):
        self.id = id


class PermissionOverwrite:
    """Mimics discord.PermissionOverwrite."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


# ═══════════════════════════════════════════════════════════════════════════════
# B. ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ButtonStyle:
    """Integer-backed enum matching real discord.py values."""
    primary = 1
    secondary = 2
    success = 3
    danger = 4
    link = 5


class ActivityType:
    """Integer-backed enum matching real discord.py values."""
    playing = 0
    streaming = 1
    listening = 2
    watching = 3
    competing = 5


# ═══════════════════════════════════════════════════════════════════════════════
# C. EMBED SYSTEM (full roundtrip support)
# ═══════════════════════════════════════════════════════════════════════════════


class Color:
    """Mimics discord.Color — callable and with static factory methods."""

    def __init__(self, value=0):
        self.value = value

    def __int__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, Color):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return NotImplemented

    @staticmethod
    def blue():
        return Color(0x3498DB)

    @staticmethod
    def red():
        return Color(0xE74C3C)

    @staticmethod
    def green():
        return Color(0x2ECC71)

    @staticmethod
    def gold():
        return Color(0xF1C40F)

    @staticmethod
    def orange():
        return Color(0xE67E22)

    @staticmethod
    def purple():
        return Color(0x9B59B6)

    @staticmethod
    def dark_grey():
        return Color(0x607D8B)

    @staticmethod
    def default():
        return Color(0)


class Embed:
    """Mimics discord.Embed with full to_dict()/from_dict() roundtrip."""

    def __init__(self, *, title="", description="", color=None):
        self.title = title
        self.description = description
        self.color = color
        self.fields = []
        self.footer = {}
        self.author = {}
        self.thumbnail = {}
        self.image = {}

    def add_field(self, *, name="", value="", inline=True):
        self.fields.append({"name": name, "value": value, "inline": inline})
        return self

    def set_footer(self, *, text="", icon_url=None):
        self.footer = {"text": text}
        if icon_url:
            self.footer["icon_url"] = icon_url
        return self

    def set_author(self, *, name="", url=None, icon_url=None):
        self.author = {"name": name}
        if url:
            self.author["url"] = url
        if icon_url:
            self.author["icon_url"] = icon_url
        return self

    def set_thumbnail(self, *, url=""):
        self.thumbnail = {"url": url}
        return self

    def set_image(self, *, url=""):
        self.image = {"url": url}
        return self

    def to_dict(self):
        d = {}
        if self.title:
            d["title"] = self.title
        if self.description:
            d["description"] = self.description
        if self.color is not None:
            d["color"] = int(self.color) if isinstance(self.color, Color) else self.color
        if self.fields:
            d["fields"] = list(self.fields)
        if self.footer:
            d["footer"] = dict(self.footer)
        if self.author:
            d["author"] = dict(self.author)
        if self.thumbnail:
            d["thumbnail"] = dict(self.thumbnail)
        if self.image:
            d["image"] = dict(self.image)
        return d

    @classmethod
    def from_dict(cls, data):
        e = cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            color=data.get("color"),
        )
        for f in data.get("fields", []):
            e.add_field(
                name=f.get("name", ""),
                value=f.get("value", ""),
                inline=f.get("inline", True),
            )
        if "footer" in data:
            e.footer = dict(data["footer"])
        if "author" in data:
            e.author = dict(data["author"])
        if "thumbnail" in data:
            e.thumbnail = dict(data["thumbnail"])
        if "image" in data:
            e.image = dict(data["image"])
        return e


# ═══════════════════════════════════════════════════════════════════════════════
# D. UI COMPONENTS (discord.ui)
# ═══════════════════════════════════════════════════════════════════════════════


class View:
    """Mimics discord.ui.View — subclassable with children list."""

    def __init__(self, *, timeout=None):
        self.timeout = timeout
        self.children = []

    def add_item(self, item):
        self.children.append(item)

    def clear_items(self):
        self.children.clear()

    def stop(self):
        pass

    def is_finished(self):
        return False

    async def on_timeout(self):
        pass

    async def on_error(self, interaction, error, item):
        pass


class Select:
    """Mimics discord.ui.Select."""

    def __init__(self, *, placeholder="", options=None, row=0,
                 min_values=1, max_values=1):
        self.placeholder = placeholder
        self.options = options or []
        self.row = row
        self.values = []
        self.callback = None
        self.min_values = min_values
        self.max_values = max_values


class Button:
    """Mimics discord.ui.Button."""

    def __init__(self, *, label="", style=None, custom_id=None,
                 disabled=False, emoji=None, url=None, row=None):
        self.label = label
        self.style = style
        self.custom_id = custom_id
        self.disabled = disabled
        self.emoji = emoji
        self.url = url
        self.callback = None
        self.row = row


class SelectOption:
    """Mimics discord.SelectOption."""

    def __init__(self, *, label="", value="", description="",
                 default=False, emoji=None):
        self.label = label
        self.value = value
        self.description = description
        self.default = default
        self.emoji = emoji


def _decorator_factory(**_kw):
    """Returns an identity decorator — the decorated function is returned as-is."""
    def _decorator(fn):
        fn.__discord_ui_model_kwargs__ = _kw
        return fn
    return _decorator


def _identity_decorator(fn):
    """Pass-through decorator."""
    return fn


# discord.ui.button() and discord.ui.select() decorator factories
ui_button = _decorator_factory
ui_select = _decorator_factory


# ═══════════════════════════════════════════════════════════════════════════════
# E. VOICE (state-tracked)
# ═══════════════════════════════════════════════════════════════════════════════


class _Decoder:
    """Mimics VoiceClient.decoder attributes."""
    CHANNELS = 2
    SAMPLE_SIZE = 4  # 2 bytes * 2 channels
    SAMPLING_RATE = 48000


class VoiceClient:
    """Mimics discord.VoiceClient with connection/playback state tracking."""

    def __init__(self):
        self._connected = False
        self._playing = False
        self._recording = False
        self.decoder = _Decoder()

    def is_connected(self):
        return self._connected

    def is_playing(self):
        return self._playing

    def play(self, source, *, after=None):
        self._playing = True

    def stop(self):
        self._playing = False

    async def disconnect(self, *, force=False):
        self._connected = False
        self._playing = False

    def start_recording(self, sink, callback, channel):
        self._recording = True
        if hasattr(sink, 'init'):
            sink.init(self)

    def stop_recording(self):
        self._recording = False

    @property
    def recording(self):
        return self._recording


class FFmpegPCMAudio:
    """Mimics discord.FFmpegPCMAudio."""

    def __init__(self, source, *, before_options=None, options=None):
        self.source = source
        self.before_options = before_options
        self.options = options


class PCMVolumeTransformer:
    """Mimics discord.PCMVolumeTransformer."""

    def __init__(self, source, volume=1.0):
        self.source = source
        self.volume = volume


class DMChannel:
    """Marker class for isinstance checks."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# F. OPUS (state-tracked)
# ═══════════════════════════════════════════════════════════════════════════════


class OpusNotLoaded(Exception):
    """Raised when opus operations are attempted without loading the library."""
    pass


class _OpusModule:
    """Mimics the discord.opus module."""

    _loaded = False

    @classmethod
    def is_loaded(cls):
        return cls._loaded

    @classmethod
    def load_opus(cls, path=None):
        cls._loaded = True


# ═══════════════════════════════════════════════════════════════════════════════
# G. SINKS (discord.sinks)
# ═══════════════════════════════════════════════════════════════════════════════


class Filters:
    """Mimics discord.sinks.Filters."""

    @staticmethod
    def container(fn):
        return fn


class Sink:
    """Mimics discord.sinks.Sink — base class for voice sinks."""

    def __init__(self, *, filters=None):
        self.encoding = "wav"
        self.audio_data = {}

    def init(self, vc):
        pass

    def write(self, data, user):
        pass

    def format_audio(self, audio):
        pass

    def cleanup(self):
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# H. COMMANDS (discord.ext.commands)
# ═══════════════════════════════════════════════════════════════════════════════


class _BotUser:
    """Represents the bot's own user identity."""

    def __init__(self):
        self.id = 0
        self.name = "StubBot"

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, _BotUser):
            return self.id == other.id
        return NotImplemented

    @property
    def mention(self):
        return f"<@{self.id}>"


class Context:
    """Mimics commands.Context with message tracking."""

    def __init__(self):
        self.sent_messages = []
        self.channel = None
        self.author = None
        self.voice_client = None
        self.message = None
        self.guild = None

    async def send(self, content="", *, embed=None, view=None, file=None):
        self.sent_messages.append(content)
        return content


class CommandNotFound(Exception):
    """Raised when a command is not found."""
    pass


class Cog:
    """Base class stub for command cogs."""
    pass


class Bot:
    """Mimics commands.Bot — subclassable, supports command/event decorators."""

    def __init__(self, command_prefix="!", intents=None, help_command=None, **kw):
        self.command_prefix = command_prefix
        self.intents = intents
        self._commands = {}
        self._user = _BotUser()
        self.voice_clients = []
        self.guilds = []
        self.latency = 0.0

    @property
    def user(self):
        return self._user

    def command(self, name=None, **kw):
        def decorator(fn):
            cmd_name = name or fn.__name__
            self._commands[cmd_name] = fn
            return fn
        return decorator

    def event(self, fn):
        return fn

    def run(self, token):
        pass

    async def start(self, token):
        pass

    async def process_commands(self, msg):
        pass

    async def change_presence(self, *, activity=None, status=None):
        pass

    def get_channel(self, channel_id):
        return None


def ext_command(**kw):
    """Module-level command() decorator factory for discord.ext.commands."""
    return _identity_decorator


# ═══════════════════════════════════════════════════════════════════════════════
# I. TASKS (discord.ext.tasks) — with lifecycle tracking
# ═══════════════════════════════════════════════════════════════════════════════


class _LoopTask:
    """Wraps an async function with start/stop/cancel lifecycle."""

    def __init__(self, fn, **kw):
        self._fn = fn
        self._running = False
        self._kw = kw
        # Preserve the function's attributes
        self.__name__ = getattr(fn, '__name__', 'loop_task')

    def start(self, *args, **kwargs):
        self._running = True

    def stop(self):
        self._running = False

    def cancel(self):
        self._running = False

    def is_running(self):
        return self._running

    def restart(self, *args, **kwargs):
        self._running = True

    def change_interval(self, *, seconds=None, minutes=None, hours=None):
        pass

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    def __get__(self, obj, objtype=None):
        # Support use as a descriptor on classes (method binding)
        if obj is None:
            return self
        return self


def loop(*, seconds=0, minutes=0, hours=0, count=None, reconnect=True):
    """Mimics tasks.loop() — returns a _LoopTask wrapper."""
    def decorator(fn):
        return _LoopTask(fn, seconds=seconds, minutes=minutes, hours=hours)
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# J. APP COMMANDS (discord.app_commands)
# ═══════════════════════════════════════════════════════════════════════════════


class _AppCommandsModule:
    """Attribute-permissive namespace for discord.app_commands."""

    def __getattr__(self, name):
        return _decorator_factory

    def command(self, **kw):
        return _identity_decorator

    def describe(self, **kw):
        return _identity_decorator


# ═══════════════════════════════════════════════════════════════════════════════
# K. install() — Inject stubs into sys.modules
# ═══════════════════════════════════════════════════════════════════════════════


def install():
    """Create and inject discord stub modules into sys.modules.

    Idempotent — calling install() twice is safe.
    Returns the top-level discord module for direct use.
    """
    if "discord" in sys.modules:
        existing = sys.modules["discord"]
        if hasattr(existing, '_codex_stub'):
            return existing

    # Create module objects
    discord_mod = types.ModuleType("discord")
    discord_mod._codex_stub = True

    ui_mod = types.ModuleType("discord.ui")
    ext_mod = types.ModuleType("discord.ext")
    commands_mod = types.ModuleType("discord.ext.commands")
    tasks_mod = types.ModuleType("discord.ext.tasks")
    sinks_mod = types.ModuleType("discord.sinks")

    # ── discord.ui ──
    ui_mod.View = View
    ui_mod.Select = Select
    ui_mod.Button = Button
    ui_mod.button = ui_button
    ui_mod.select = ui_select

    # ── discord.ext.commands ──
    commands_mod.Bot = Bot
    commands_mod.CommandNotFound = CommandNotFound
    commands_mod.Cog = Cog
    commands_mod.command = ext_command

    # ── discord.ext.tasks ──
    tasks_mod.loop = loop

    # ── discord.sinks ──
    sinks_mod.Sink = Sink
    sinks_mod.Filters = Filters

    # ── Wire submodule relationships ──
    ext_mod.commands = commands_mod
    ext_mod.tasks = tasks_mod
    discord_mod.ui = ui_mod
    discord_mod.ext = ext_mod
    discord_mod.sinks = sinks_mod

    # ── Top-level discord attributes ──
    discord_mod.Interaction = Interaction
    discord_mod.SelectOption = SelectOption
    discord_mod.Intents = Intents
    discord_mod.Embed = Embed
    discord_mod.Color = Color
    discord_mod.Colour = Color  # alias used by some code
    discord_mod.ButtonStyle = ButtonStyle
    discord_mod.ActivityType = ActivityType
    discord_mod.Activity = Activity
    discord_mod.PermissionOverwrite = PermissionOverwrite
    discord_mod.Object = Object
    discord_mod.File = File
    discord_mod.FFmpegPCMAudio = FFmpegPCMAudio
    discord_mod.PCMVolumeTransformer = PCMVolumeTransformer
    discord_mod.VoiceClient = VoiceClient
    discord_mod.DMChannel = DMChannel
    discord_mod.opus = _OpusModule
    discord_mod.app_commands = _AppCommandsModule()
    discord_mod.Client = type("Client", (), {})

    # ── Inject into sys.modules ──
    sys.modules["discord"] = discord_mod
    sys.modules["discord.ui"] = ui_mod
    sys.modules["discord.ext"] = ext_mod
    sys.modules["discord.ext.commands"] = commands_mod
    sys.modules["discord.ext.tasks"] = tasks_mod
    sys.modules["discord.sinks"] = sinks_mod

    return discord_mod
