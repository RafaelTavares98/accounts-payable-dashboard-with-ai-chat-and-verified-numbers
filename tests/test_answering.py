"""One question, from the click to the sentence.

The order matters and the tests pin it:

1. the model names the panels,
2. code computes every figure,
3. the model is handed those figures and writes the sentence.

Step three happens last so that the model has nothing to invent. The
figures already exist by the time it is asked for words.
"""

import json
from decimal import Decimal

import answering


def plan(*names):
    return json.dumps({'panels': list(names), 'reason': 'because'})


class TestTalkingToIt:
    """It answered "hi" with a canned paragraph, then answered "I just
    said hi" with the same paragraph, word for word. That is not a
    conversation, it is a vending machine."""

    def test_a_greeting_is_written_by_the_model(self, owed, today,
                                                fake_model):
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}),
                           'Hello. Ask me about the invoices.')

        answer = answering.answer('hi', owed, today=today, model=model)

        assert answer.sentence == 'Hello. Ask me about the invoices.'

    def test_it_sees_what_was_said_before(self, owed, today, fake_model):
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}),
                           'You did. What would you like to know?')

        answering.answer('I just said hi', owed, today=today, model=model,
                         history=[{'role': 'user', 'text': 'hi'},
                                  {'role': 'bot', 'text': 'Hello.'}])

        assert 'hi' in model.calls[0]
        assert 'Hello.' in model.calls[0]

    def test_a_figure_in_small_talk_is_still_refused(self, owed, today,
                                                     fake_model):
        """No figure was computed for a greeting, so every number in it
        is invented by definition."""
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}),
                           'Hi. You owe 999,999.00 by the way.')

        answer = answering.answer('hi', owed, today=today, model=model)

        assert '999,999.00' not in answer.sentence

    def test_history_reaches_a_real_question_too(self, owed, today,
                                                 fake_model):
        """"And for Marsk?" only means something next to the question
        before it."""
        model = fake_model(plan('balance'), '5,500.00 is owed.')

        answering.answer('and for Marsk?', owed, today=today, model=model,
                         history=[{'role': 'user',
                                   'text': 'what do we owe?'}])

        assert 'what do we owe?' in model.calls[0]


class TestTheHappyPath:
    def test_the_panels_the_model_asked_for_are_built(self, owed, today,
                                                      fake_model):
        model = fake_model(plan('overdue', 'by_band'),
                           '3,483 accounts are late.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert [panel.name for panel in answer.panels][:2] == \
            ['overdue', 'by_band']

    def test_the_figures_are_real(self, owed, today, fake_model):
        model = fake_model(plan('overdue'), 'Some words.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert dict(answer.panels[0].rows)['Overdue'] == Decimal('31750.00')

    def test_the_sentence_comes_back(self, owed, today, fake_model):
        model = fake_model(plan('overdue'),
                           '31,750.00 is overdue across 4 documents.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert answer.sentence == \
            '31,750.00 is overdue across 4 documents.'

    def test_exactly_two_model_calls(self, owed, today, fake_model):
        """One to choose the panels, one to write the sentence. A third
        call means something is asking the model twice for the same
        thing, and every call costs money and a second of waiting."""
        model = fake_model(plan('overdue'), 'Some words.')

        answering.answer('how much is late?', owed, today=today,
                         model=model)

        assert len(model.calls) == 2


class TestTheBrief:
    """The model was handed four figures and asked to explain a fall.
    It cannot: nothing it was given describes one. The brief is the
    whole slice, computed by code, so an explanation has something
    true to be built out of."""

    def test_the_brief_carries_the_headline(self, owed, today):
        brief = answering.brief(owed, today)

        assert '67,450.00' in brief
        assert '10 documents' in brief

    def test_it_names_the_biggest_suppliers(self, owed, today):
        brief = answering.brief(owed, today)

        assert 'Guangzhou Verrelia Glassworks Co., Ltd.' in brief

    def test_it_carries_the_weekly_series(self, owed, today):
        brief = answering.brief(owed, today)

        assert 'falling due by week' in brief.lower()
        assert 'arrived by week' in brief.lower()

    def test_it_names_the_sharpest_fall(self, owed, today):
        """The one thing a why question is usually about."""
        brief = answering.brief(owed, today)

        assert 'sharpest fall' in brief.lower()

    def test_the_brief_reaches_the_model(self, owed, today, fake_model):
        model = fake_model(plan('balance'), 'Some words.')

        answering.answer('why did it drop?', owed, today=today,
                         model=model)

        assert '67,450.00' in model.calls[1]

    def test_the_question_reaches_the_model_with_it(self, owed, today,
                                                    fake_model):
        model = fake_model(plan('balance'), 'Some words.')

        answering.answer('why did it drop?', owed, today=today,
                         model=model)

        assert 'why did it drop?' in model.calls[1]

    def test_a_figure_from_the_brief_is_allowed_through(self, owed, today,
                                                        fake_model):
        """Every number in the brief was computed, so quoting one back
        is not inventing it."""
        model = fake_model(plan('balance'),
                           'Guangzhou Verrelia Glassworks Co., Ltd. is '
                           'owed 25,500.00, the largest of the ten.')

        answer = answering.answer('why did it drop?', owed, today=today,
                                  model=model)

        assert not answer.rejected

    def test_a_figure_from_nowhere_is_still_refused(self, owed, today,
                                                    fake_model):
        model = fake_model(plan('balance'),
                           'Arrivals fell to 77,777.77 in May.')

        answer = answering.answer('why did it drop?', owed, today=today,
                                  model=model)

        assert answer.rejected


class TestTheSecondCall:
    def test_the_figures_are_in_the_prompt(self, owed, today, fake_model):
        """This is the only moment the model sees a number, and it sees
        it as something already decided."""
        model = fake_model(plan('overdue'), 'Some words.')

        answering.answer('how much is late?', owed, today=today,
                         model=model)

        assert '31750.00' in model.calls[1]

    def test_no_rows_are_in_the_prompt(self, owed, today, fake_model):
        model = fake_model(plan('overdue'), 'Some words.')

        answering.answer('how much is late?', owed, today=today,
                         model=model)

        assert 'NCL-2026-3001' not in model.calls[1]

    def test_the_prompt_forbids_new_numbers(self, owed, today, fake_model):
        """Telling it not to is weak. It is still worth doing, because
        the check below is what actually holds."""
        model = fake_model(plan('overdue'), 'Some words.')

        answering.answer('how much is late?', owed, today=today,
                         model=model)

        assert 'only the figures given' in model.calls[1].lower()

    def test_the_question_is_in_the_prompt(self, owed, today, fake_model):
        """It is asked to answer a question it was never shown."""
        model = fake_model(plan('overdue'), 'Some words.')

        answering.answer('how much is late?', owed, today=today,
                         model=model)

        assert 'how much is late?' in model.calls[1]


class TestTheModelCannotInventAFigure:
    def test_a_sentence_with_a_figure_nobody_computed_is_rejected(
            self, owed, today, fake_model):
        """The hard one. The model is handed 31,750.00 and writes
        99,999.00 instead. The answer must not carry that sentence."""
        model = fake_model(plan('overdue'),
                           '99,999.00 is overdue across 7 documents.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert answer.rejected
        assert '99,999.00' not in answer.sentence

    def test_the_panels_survive_a_rejected_sentence(self, owed, today,
                                                    fake_model):
        """The numbers were right. Only the words were wrong, so the
        words are replaced and the charts stay."""
        model = fake_model(plan('overdue'), '99,999.00 is overdue.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert answer.panels
        assert dict(answer.panels[0].rows)['Overdue'] == Decimal('31750.00')

    def test_the_replacement_sentence_is_written_by_code(self, owed, today,
                                                         fake_model):
        model = fake_model(plan('overdue'), '99,999.00 is overdue.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert '31,750.00' in answer.sentence

    def test_a_figure_that_matches_is_allowed_through(self, owed, today,
                                                      fake_model):
        model = fake_model(plan('overdue'),
                           '31,750.00 is overdue across 4 documents, '
                           'an average of 31.5 days late.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert not answer.rejected

    def test_a_figure_at_the_end_of_a_sentence_is_not_invented(
            self, owed, today, fake_model):
        """The token matcher was swallowing the full stop, so
        "31,750.00." never matched "31,750.00" and every sentence that
        ended on its figure was thrown away. Most of them do."""
        model = fake_model(plan('overdue'),
                           'The amount overdue is 31,750.00.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert not answer.rejected

    def test_a_figure_before_a_comma_is_not_invented(self, owed, today,
                                                     fake_model):
        model = fake_model(plan('overdue'),
                           'Overdue is 31,750.00, which is 40.0%.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert not answer.rejected

    def test_a_year_in_the_sentence_is_not_an_invented_figure(
            self, owed, today, fake_model):
        """`2026` is a date, not a total. Treating every digit as a
        figure would reject every sentence ever written."""
        model = fake_model(plan('overdue'),
                           'Since March 2026, 31,750.00 has gone overdue.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert not answer.rejected


class TestItSaysWhichRowsItUsed:
    def test_the_answer_names_the_slice(self, owed, today, fake_model):
        """The video's own sentence says "no filtro atual do painel".
        A figure without its slice is a figure nobody can check."""
        model = fake_model(plan('overdue'), '31,750.00 is overdue.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert answer.rows_used == 10

    def test_it_names_the_date_the_lateness_was_measured_from(
            self, owed, today, fake_model):
        model = fake_model(plan('overdue'), '31,750.00 is overdue.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert answer.as_of == today

    def test_every_figure_can_be_traced_to_its_function(self, owed, today,
                                                        fake_model):
        """The audit trail. For each number shown, which function
        produced it, over how many rows."""
        model = fake_model(plan('overdue', 'by_supplier'), 'Some words.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        for figure in answer.figures:
            assert figure.name
            assert figure.function
            assert figure.rows == 10


class TestTheFiltersAreObeyed:
    def test_the_answer_is_computed_over_the_filtered_rows(
            self, owed, today, fake_model):
        import filtering
        marsk = filtering.apply(owed, supplier='Marsk Line Agencies B.V.')
        model = fake_model(plan('balance'), '5,500.00 is owed.')

        answer = answering.answer('what do we owe Marsk?', marsk,
                                  today=today, model=model)

        assert dict(answer.panels[0].rows)['Total owed'] == \
            Decimal('5500.00')

    def test_the_unfiltered_total_never_leaks_in(self, owed, today,
                                                 fake_model):
        import filtering
        marsk = filtering.apply(owed, supplier='Marsk Line Agencies B.V.')
        model = fake_model(plan('balance'), '67,450.00 is owed.')

        answer = answering.answer('what do we owe Marsk?', marsk,
                                  today=today, model=model)

        assert answer.rejected
