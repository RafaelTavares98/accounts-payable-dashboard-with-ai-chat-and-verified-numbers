"""The one place that knows DeepSeek exists.

Everything else takes a model as an argument. This builds the function
they take.
"""

import os

import httpx

TIMEOUT_SECONDS = 20

DEEPSEEK_URL = 'https://api.deepseek.com/chat/completions'

MODEL = 'deepseek-v4-pro'

#: Naming panels off a fixed menu is a classification, not a piece of
#: writing. It takes the cheap model: a quarter of the price and a
#: fraction of the wait.
ROUTING_MODEL = 'deepseek-flash'


class ModelFailed(Exception):
    """The model could not be asked, or answered with nothing usable."""


#: Where the key may be sitting, in the order they are tried. The second
#: pair is the one the earlier projects on this account already wrote, so
#: nobody has to paste the key a second time.
KEYRING_ENTRIES = (
    ('payables-panel', 'deepseek'),
    ('deepseek', 'api-key'),
)


def _from_keyring():
    try:
        import keyring
    except Exception:
        return None
    for service, user in KEYRING_ENTRIES:
        try:
            found = keyring.get_password(service, user)
        except Exception:
            continue
        if found:
            return found
    return None


def key():
    """The API key. Environment first, the Windows keyring second,
    nothing when both are empty."""
    from_environment = os.environ.get('DEEPSEEK_API_KEY')
    if from_environment:
        return from_environment
    return _from_keyring()


def deepseek(key=None, transport=None):
    """Build the ask function every other module takes.

    The key and the transport are arguments so no test ever reaches the
    network. In production both come from the real world.
    """
    transport = transport or httpx

    def ask(prompt):
        wants_json = 'json' in prompt.lower()
        body = {
            # Routing is a choice between seven names. It goes to the
            # cheap, fast model; only the sentence needs the better one.
            'model': ROUTING_MODEL if wants_json else MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        if wants_json:
            body['response_format'] = {'type': 'json_object'}
        reply = transport.post(
            DEEPSEEK_URL,
            json=body,
            headers={'Authorization': f'Bearer {key}'},
            timeout=TIMEOUT_SECONDS,
        )
        if reply.status_code != 200:
            raise ModelFailed(
                f'the model answered with status {reply.status_code}')
        data = reply.json()
        choices = data.get('choices') or []
        if not choices:
            raise ModelFailed('the model answered with no choices')
        return choices[0]['message']['content']

    return ask
