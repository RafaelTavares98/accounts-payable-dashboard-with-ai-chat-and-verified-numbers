"""One question on the cost view, from the click to the sentence.

The order matters and the tests pin it:

1. the model names the panels,
2. code computes every figure,
3. the model is handed those figures and writes the sentence.

Step three happens last so that the model has nothing to invent. The
figures already exist by the time it is asked for words. The guard in
answering.py is shared with the anomaly view and is unchanged.
"""

import json
from decimal import Decimal

import cost
import cost_answering as answering

D = Decimal


def plan(*names):
    return json.dumps({'panels': list(names), 'reason': 'because'})


def ask(question, lines, model, **extra):
    from conftest import TODAY
    return answering.answer(question, lines, today=TODAY, model=model,
                            **extra)


class TestTalkingToIt:
    def test_a_greeting_is_written_by_the_model(self, lines, fake_model):
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}),
                           'Hello. Ask me about the landed cost.')

        answer = ask('hi', lines, model)

        assert answer.sentence == 'Hello. Ask me about the landed cost.'

    def test_it_sees_what_was_said_before(self, lines, fake_model):
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}),
                           'You did. What would you like to know?')

        ask('I just said hi', lines, model,
            history=[{'role': 'user', 'text': 'hi'},
                     {'role': 'bot', 'text': 'Hello.'}])

        assert 'hi' in model.calls[0]
        assert 'Hello.' in model.calls[0]

    def test_a_figure_in_small_talk_is_still_refused(self, lines,
                                                     fake_model):
        """No figure was computed for a greeting, so every number in it
        is invented by definition."""
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}),
                           'Hi. It cost 999,999.00 by the way.')

        assert '999,999.00' not in ask('hi', lines, model).sentence


class TestTheHappyPath:
    def test_the_panels_the_model_asked_for_are_built(self, lines,
                                                      fake_model):
        model = fake_model(plan('landed', 'by_component'), 'Some words.')

        answer = ask('what did it cost?', lines, model)

        assert [p.name for p in answer.panels][:2] == \
            ['landed', 'by_component']

    def test_the_figures_are_real(self, lines, fake_model):
        model = fake_model(plan('landed'), 'Some words.')

        answer = ask('what did it cost?', lines, model)

        assert dict(answer.panels[0].rows)['Landed cost'] == D('24659.00')

    def test_the_sentence_comes_back(self, lines, fake_model):
        model = fake_model(plan('landed'), 'The parts cost 24,659.00 to land.')

        answer = ask('what did it cost?', lines, model)

        assert answer.sentence == 'The parts cost 24,659.00 to land.'
        assert not answer.rejected

    def test_exactly_two_model_calls(self, lines, fake_model):
        """One to choose the panels, one to write the sentence."""
        model = fake_model(plan('landed'), 'Some words.')

        ask('what did it cost?', lines, model)

        assert len(model.calls) == 2


class TestTheBrief:
    def test_the_brief_carries_the_headline(self, lines):
        brief = answering.brief(lines)

        assert '24,659.00' in brief
        assert '3 shipments' in brief

    def test_it_names_the_carriers_and_the_parts(self, lines):
        brief = answering.brief(lines)

        assert 'Marsk Line Agencies B.V.' in brief
        assert 'Lotion pump, 24 mm' in brief

    def test_it_carries_the_months(self, lines):
        assert '2026-05 final 7,074.50 provisional 1,100.00' in \
            answering.brief(lines)

    def test_the_brief_reaches_the_model(self, lines, fake_model):
        model = fake_model(plan('landed'), 'Some words.')

        ask('why is it so high?', lines, model)

        assert '24,659.00' in model.calls[1]
        assert 'why is it so high?' in model.calls[1]

    def test_a_figure_from_the_brief_is_allowed_through(self, lines,
                                                        fake_model):
        model = fake_model(plan('landed'),
                           'Marsk Line Agencies B.V. moved 16,484.50 of it.')

        assert not ask('who moved it?', lines, model).rejected

    def test_a_figure_from_nowhere_is_still_refused(self, lines, fake_model):
        model = fake_model(plan('landed'), 'Freight rose to 77,777.77 in May.')

        assert ask('why?', lines, model).rejected


class TestTheSecondCall:
    def test_no_line_is_in_the_prompt(self, lines, fake_model):
        model = fake_model(plan('landed'), 'Some words.')

        ask('what did it cost?', lines, model)

        assert 'PO-1' not in model.calls[1]

    def test_the_prompt_forbids_new_numbers(self, lines, fake_model):
        model = fake_model(plan('landed'), 'Some words.')

        ask('what did it cost?', lines, model)

        assert 'only the figures given' in model.calls[1].lower()


class TestTheModelCannotInventAFigure:
    def test_a_sentence_with_a_figure_nobody_computed_is_rejected(
            self, lines, fake_model):
        """The model is handed 24,659.00 and writes 99,999.00 instead."""
        model = fake_model(plan('landed'), 'It cost 99,999.00 to land.')

        answer = ask('what did it cost?', lines, model)

        assert answer.rejected
        assert '99,999.00' not in answer.sentence

    def test_the_panels_survive_a_rejected_sentence(self, lines, fake_model):
        model = fake_model(plan('landed'), 'It cost 99,999.00.')

        answer = ask('what did it cost?', lines, model)

        assert dict(answer.panels[0].rows)['Landed cost'] == D('24659.00')

    def test_the_replacement_sentence_is_written_by_code(self, lines,
                                                         fake_model):
        model = fake_model(plan('landed'), 'It cost 99,999.00.')

        assert '24,659.00' in ask('what did it cost?', lines, model).sentence

    def test_a_figure_at_the_end_of_a_sentence_is_not_invented(
            self, lines, fake_model):
        model = fake_model(plan('landed'), 'The landed cost is 24,659.00.')

        assert not ask('what did it cost?', lines, model).rejected

    def test_a_share_is_not_invented(self, lines, fake_model):
        model = fake_model(plan('landed'),
                           '1,100.00 is provisional, which is 4.5%.')

        assert not ask('what is provisional?', lines, model).rejected

    def test_a_year_is_not_an_invented_figure(self, lines, fake_model):
        model = fake_model(plan('landed'),
                           'Since April 2026 it cost 24,659.00.')

        assert not ask('what did it cost?', lines, model).rejected


class TestItSaysWhichLinesItUsed:
    def test_the_answer_names_the_slice(self, lines, fake_model):
        model = fake_model(plan('landed'), 'Some words.')

        answer = ask('what did it cost?', lines, model)

        assert answer.rows_used == 4

    def test_every_panel_can_be_traced_to_its_function(self, lines,
                                                       fake_model):
        """For each panel shown, which function produced it, over how
        many lines."""
        model = fake_model(plan('landed', 'by_carrier'), 'Some words.')

        answer = ask('what did it cost?', lines, model)

        for figure in answer.figures:
            assert figure.function.startswith('cost.')
            assert callable(getattr(cost, figure.function[5:]))
            assert figure.rows == 4


class TestTheFiltersAreObeyed:
    def test_the_answer_is_computed_over_the_filtered_lines(self, lines,
                                                            fake_model):
        air = cost.only(lines, mode='air')
        model = fake_model(plan('landed'), 'Some words.')

        answer = ask('what did air cost?', air, model)

        assert dict(answer.panels[0].rows)['Landed cost'] == D('7074.50')

    def test_the_unfiltered_total_never_leaks_in(self, lines, fake_model):
        air = cost.only(lines, mode='air')
        model = fake_model(plan('landed'), 'It cost 24,659.00.')

        assert ask('what did air cost?', air, model).rejected
