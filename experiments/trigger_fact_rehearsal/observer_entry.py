"""Bind both existing default/shadow slots; preserve the renderer and flags."""
import shlex


def bind_authority(raw, authority_path):
    lines = raw.splitlines(keepends=True)
    slots = [i for i, line in enumerate(lines)
             if line.lstrip().startswith(b'view_authority=')]
    if len(slots) != 2:
        raise ValueError('REGISTERED_DEFAULT_AND_SHADOW_SLOTS_REQUIRED')
    token = shlex.quote(authority_path).encode()
    for i in slots:
        old = lines[i]
        indent = old[:len(old) - len(old.lstrip())]
        ending = b'\r\n' if old.endswith(b'\r\n') else b'\n' if old.endswith(b'\n') else b''
        lines[i] = indent + b'view_authority=' + token + ending
    return b''.join(lines)
