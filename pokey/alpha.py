from . import _impl

_the_pokey = _impl.Pokey._make_new(f"{__name__}._the_pokey")

injects = _the_pokey.injects
wants = _the_pokey.wants
slot_names = _the_pokey.slot_names
