"""When the honest answer is that there is no answer.

A dashboard that always produces a number is worse than one that
sometimes says no, because the reader cannot tell the two apart.

Three cases. The column does not exist. The filter left too little to say
anything about. The model could not be reached.
"""

import json

import cost_answering as answering
import cost_panels


def plan(*names):
    return json.dumps({'panels': list(names), 'reason': 'because'})


def ask(question, lines, model):
    from conftest import TODAY
    return answering.answer(question, lines, today=TODAY, model=model)


class TestAColumnThatDoesNotExist:
    def test_a_question_about_cost_centres_is_refused(self, lines,
                                                      fake_model):
        """The cost report carries no cost centre, and guessing one from
        the part would be inventing data."""
        model = fake_model(plan('by_cost_centre'))

        answer = ask('what does logistics spend?', lines, model)

        assert 'cost centre' in answer.refusal.lower()
        assert answer.panels == []

    def test_a_question_about_payments_is_refused(self, lines, fake_model):
        """The department does not pay invoices. Nothing here says when
        anything was paid."""
        model = fake_model(plan('by_payment_date'))

        assert ask('when did we pay these?', lines, model).refusal


class TestTooLittleData:
    def test_a_filter_that_leaves_nothing_is_refused(self, fake_model):
        answer = ask('what did it cost?', [], fake_model())

        assert 'filter' in answer.refusal.lower()

    def test_a_trend_over_one_line_is_refused(self, lines, fake_model):
        """One line has no trend worth printing."""
        model = fake_model(plan('by_month'), 'Some words.')

        assert ask('how is it trending?', lines[:1], model).refusal

    def test_a_total_over_one_line_is_fine(self, lines, fake_model):
        """Adding up one thing is not a statistic. It is adding up."""
        model = fake_model(plan('landed'), 'It cost 5,307.50.')

        assert not ask('what did it cost?', lines[:1], model).refusal

    def test_the_threshold_is_written_down_not_guessed(self):
        assert answering.ENOUGH_FOR_A_TREND >= 2


class TestTheModelCannotBeReached:
    def test_the_page_says_so_instead_of_breaking(self, lines):
        def broken(prompt):
            raise ConnectionError('deepseek is unreachable')

        assert ask('what did it cost?', lines, broken).refusal

    def test_a_failure_on_the_second_call_keeps_the_panels(self, lines):
        """The panels are real and must survive the API going down."""
        calls = []

        def dies_on_the_second(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                return plan('landed')
            raise ConnectionError('deepseek is unreachable')

        answer = ask('what did it cost?', lines, dies_on_the_second)

        assert answer.panels
        assert answer.sentence
        assert not answer.refusal

    def test_the_dashboard_keeps_working_without_the_model(self, lines):
        """The base view is computed by code. It never needed the model."""
        assert cost_panels.build('landed', lines).rows


class TestWhatARefusalLooksLike:
    def test_a_refusal_is_a_sentence_not_an_error_code(self, lines,
                                                       fake_model):
        answer = ask('what does logistics spend?', lines,
                     fake_model(plan('by_cost_centre')))

        assert answer.refusal.endswith('.')
        assert answer.sentence == ''

    def test_a_refusal_is_never_silent(self, lines, fake_model):
        assert ask('what did it cost?', lines, fake_model('not json')).refusal
