"""When the honest answer is that there is no answer.

A dashboard that always produces a number is worse than one that
sometimes says no, because the reader cannot tell the two apart.

Three cases. The column does not exist. The filter left too little to say
anything about. The model could not be reached.
"""

import json

import answering


def plan(*names):
    return json.dumps({'panels': list(names), 'reason': 'because'})


class TestAColumnThatDoesNotExist:
    def test_a_question_about_cost_centres_is_refused(self, owed, today,
                                                      fake_model):
        """The reference video filters by cost centre. An invoice does
        not carry one, and guessing it from the supplier would be
        inventing data."""
        model = fake_model(json.dumps({'panels': ['by_cost_centre'],
                                       'reason': 'the user asked'}))

        answer = answering.answer('what does logistics spend?', owed,
                                  today=today, model=model)

        assert answer.refusal

    def test_the_refusal_says_which_column_is_missing(self, owed, today,
                                                      fake_model):
        model = fake_model(json.dumps({'panels': ['by_cost_centre'],
                                       'reason': 'the user asked'}))

        answer = answering.answer('what does logistics spend?', owed,
                                  today=today, model=model)

        assert 'cost centre' in answer.refusal.lower()

    def test_it_does_not_answer_a_different_question_instead(
            self, owed, today, fake_model):
        """Showing the supplier breakdown because the cost centre one is
        missing answers a question nobody asked, under the heading of
        the one they did."""
        model = fake_model(json.dumps({'panels': ['by_cost_centre'],
                                       'reason': 'the user asked'}))

        answer = answering.answer('what does logistics spend?', owed,
                                  today=today, model=model)

        assert answer.panels == []

    def test_a_question_about_payment_dates_is_refused(self, owed, today,
                                                       fake_model):
        """Nothing in an invoice says when it was paid, or whether it
        was."""
        model = fake_model(json.dumps({'panels': ['by_payment_date'],
                                       'reason': 'the user asked'}))

        answer = answering.answer('when did we pay these?', owed,
                                  today=today, model=model)

        assert answer.refusal


class TestTooLittleData:
    def test_a_filter_that_leaves_nothing_is_refused(self, today,
                                                     fake_model):
        model = fake_model(plan('balance'), 'Nothing is owed.')

        answer = answering.answer('what do we owe?', [],
                                  today=today, model=model)

        assert answer.refusal

    def test_the_refusal_says_the_filter_is_the_reason(self, today,
                                                       fake_model):
        model = fake_model(plan('balance'), 'Nothing is owed.')

        answer = answering.answer('what do we owe?', [],
                                  today=today, model=model)

        assert 'filter' in answer.refusal.lower()

    def test_an_average_over_one_document_is_refused(self, owed, today,
                                                     fake_model):
        """One invoice has no spread, no trend and no average worth
        printing. Printing it anyway makes a sample of one look like a
        finding."""
        one = owed[:1]
        model = fake_model(plan('by_month'), 'Some words.')

        answer = answering.answer('how is it trending?', one,
                                  today=today, model=model)

        assert answer.refusal

    def test_a_count_over_one_document_is_fine(self, owed, today,
                                               fake_model):
        """Counting one thing is not a statistic. It is counting."""
        one = owed[:1]
        model = fake_model(plan('balance'), '10,000.00 is owed.')

        answer = answering.answer('what do we owe?', one,
                                  today=today, model=model)

        assert not answer.refusal

    def test_the_threshold_is_written_down_not_guessed(self):
        """A rule buried in an `if` is a rule nobody can argue with."""
        assert answering.ENOUGH_FOR_A_TREND >= 2


class TestTheModelCannotBeReached:
    def test_the_page_says_so_instead_of_breaking(self, owed, today):
        def broken(prompt):
            raise ConnectionError('deepseek is unreachable')

        answer = answering.answer('what do we owe?', owed,
                                  today=today, model=broken)

        assert answer.refusal

    def test_a_failure_on_the_second_call_is_a_refusal(self, owed, today):
        """The first call worked, the panels were built, and then the API
        went down. The panels are real and must survive."""
        calls = []

        def dies_on_the_second(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                return plan('overdue')
            raise ConnectionError('deepseek is unreachable')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=dies_on_the_second)

        assert answer.panels
        assert answer.sentence
        assert not answer.refusal

    def test_the_dashboard_keeps_working_without_the_model(self, owed,
                                                           today):
        """The base view is computed by code. It never needed the model,
        and it must not go dark when the model does.

        This is the same choice the reference makes: the local model sits
        behind a button, and the panel works before anybody presses it.
        """
        import panels
        built = panels.build('balance', owed, today=today)

        assert built.rows


class TestWhatARefusalLooksLike:
    def test_a_refusal_is_a_sentence_not_an_error_code(self, owed, today,
                                                       fake_model):
        model = fake_model(json.dumps({'panels': ['by_cost_centre'],
                                       'reason': 'the user asked'}))

        answer = answering.answer('what does logistics spend?', owed,
                                  today=today, model=model)

        assert answer.refusal.endswith('.')

    def test_a_refusal_carries_no_sentence_of_its_own(self, owed, today,
                                                      fake_model):
        """Two messages in the chat, one saying no and one saying a
        number, is two answers to one question."""
        model = fake_model(json.dumps({'panels': ['by_cost_centre'],
                                       'reason': 'the user asked'}))

        answer = answering.answer('what does logistics spend?', owed,
                                  today=today, model=model)

        assert answer.sentence == ''

    def test_a_refusal_is_never_silent(self, owed, today, fake_model):
        model = fake_model('not json')

        answer = answering.answer('what do we owe?', owed,
                                  today=today, model=model)

        assert answer.refusal
