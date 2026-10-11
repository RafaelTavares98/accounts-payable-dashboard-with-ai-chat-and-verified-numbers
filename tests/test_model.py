"""The one place that knows DeepSeek exists.

Everything else takes a model as an argument. This builds the function
they take. It is tested against a fake transport, never against the real
API, because a test that needs a key and a signal is a test nobody runs.
"""

import json

import pytest

import model


class FakeTransport:
    """Stands in for httpx. Records the request, returns a canned body."""

    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.sent = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.sent.append({'url': url, 'json': json, 'headers': headers})
        return FakeReply(self.body, self.status)


class FakeReply:
    def __init__(self, body, status):
        self._body = body
        self.status_code = status
        self.text = json.dumps(body)

    def json(self):
        return self._body


def a_reply(content):
    return {'choices': [{'message': {'content': content}}]}


class TestTheRequest:
    def test_it_calls_the_documented_url(self):
        transport = FakeTransport(a_reply('hello'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('a prompt')

        assert transport.sent[0]['url'] == \
            'https://api.deepseek.com/chat/completions'

    def test_a_json_prompt_goes_to_the_cheap_fast_model(self):
        """Picking from a menu of seven names is a classification. It
        does not need the expensive model, and the expensive model is
        where most of the twenty second wait came from."""
        transport = FakeTransport(a_reply('{}'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('answer in json please')

        assert transport.sent[0]['json']['model'] == 'deepseek-flash'

    def test_writing_the_sentence_keeps_the_better_model(self):
        transport = FakeTransport(a_reply('words'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('write one sentence')

        assert transport.sent[0]['json']['model'] == 'deepseek-v4-pro'

    def test_it_sends_the_model_rafael_chose(self):
        transport = FakeTransport(a_reply('hello'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('a prompt')

        assert transport.sent[0]['json']['model'] == 'deepseek-v4-pro'

    def test_the_key_travels_in_the_header_not_the_body(self):
        transport = FakeTransport(a_reply('hello'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('a prompt')

        assert transport.sent[0]['headers']['Authorization'] == \
            'Bearer sk-test'
        assert 'sk-test' not in json.dumps(transport.sent[0]['json'])

    def test_a_prompt_asking_for_json_turns_json_mode_on(self):
        """DeepSeek needs both: the word json in the prompt and the
        response_format field. One without the other fails at runtime."""
        transport = FakeTransport(a_reply('{}'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('answer in json please')

        assert transport.sent[0]['json']['response_format'] == \
            {'type': 'json_object'}

    def test_a_prompt_not_asking_for_json_leaves_it_off(self):
        transport = FakeTransport(a_reply('words'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('write one sentence')

        assert 'response_format' not in transport.sent[0]['json']

    def test_it_gives_up_rather_than_hanging(self):
        """A dashboard that waits forever is a dashboard that is down,
        without saying so."""
        transport = FakeTransport(a_reply('hello'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('a prompt')

        assert transport.sent[0] and model.TIMEOUT_SECONDS <= 30


class TestTheReply:
    def test_the_content_comes_back_as_a_string(self):
        transport = FakeTransport(a_reply('the answer'))
        ask = model.deepseek(key='sk-test', transport=transport)

        assert ask('a prompt') == 'the answer'

    def test_an_error_status_raises(self):
        """`routing` catches it and turns it into a refusal. It must be
        allowed to reach there."""
        transport = FakeTransport({'error': 'nope'}, status=401)
        ask = model.deepseek(key='sk-test', transport=transport)

        with pytest.raises(model.ModelFailed):
            ask('a prompt')

    def test_the_key_is_not_in_the_error(self):
        transport = FakeTransport({'error': 'nope'}, status=401)
        ask = model.deepseek(key='sk-do-not-leak-this',
                             transport=transport)

        try:
            ask('a prompt')
        except model.ModelFailed as failed:
            assert 'sk-do-not-leak-this' not in str(failed)

    def test_a_reply_with_no_choices_raises(self):
        transport = FakeTransport({'choices': []})
        ask = model.deepseek(key='sk-test', transport=transport)

        with pytest.raises(model.ModelFailed):
            ask('a prompt')


class TestWhereTheKeyComesFrom:
    def test_the_environment_is_read_first(self, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-from-env')

        assert model.key() == 'sk-from-env'

    def test_the_keyring_is_the_fallback(self, monkeypatch):
        """The same place the invoice pipeline keeps its mail password.
        An environment variable sits in plain text in the registry."""
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setattr(model, '_from_keyring',
                            lambda: 'sk-from-keyring')

        assert model.key() == 'sk-from-keyring'

    def test_no_key_anywhere_is_not_a_crash(self, monkeypatch):
        """The dashboard opens without one. Only typing needs it."""
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setattr(model, '_from_keyring', lambda: None)

        assert model.key() is None
