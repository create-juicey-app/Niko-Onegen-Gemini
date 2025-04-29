# This file makes the gui_mixins directory a Python package.

# Import mixins to make them easily accessible (optional, but can be convenient)
from .resources import ResourcesMixin
from .dialogue import DialogueMixin
from .input import InputMixin
from .choices import ChoicesMixin
from .effects import EffectsMixin
from .rendering import RenderingMixin
from .events import EventsMixin
from .options_menu import OptionsMenuMixin
# Add the new mixins
from .rendering_components import RenderingComponentsMixin
from .event_handlers import EventHandlersMixin
