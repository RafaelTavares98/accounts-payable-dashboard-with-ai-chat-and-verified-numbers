"""How many panels an anomaly question opens.

One question opens one panel at most, and a question whose answer is a
single figure opens none. A sentence does not need a picture beside it.
"""

import anomaly_answering as asking


class TestAChip:

    def test_a_count_question_opens_no_panel(self, anomaly_rows):
        chip = next(c for c in asking.CHIPS
                    if c.question == 'How many invoices were flagged?')
        assert asking.click(chip, anomaly_rows).panels == []

    def test_but_it_still_answers(self, anomaly_rows):
        chip = next(c for c in asking.CHIPS
                    if c.question == 'How many invoices were flagged?')
        assert 'flagged' in asking.click(chip, anomaly_rows).sentence

    def test_a_breakdown_question_opens_one_panel(self, anomaly_rows):
        chip = next(c for c in asking.CHIPS
                    if c.question == 'Whose errors are they?')
        assert len(asking.click(chip, anomaly_rows).panels) == 1

    def test_the_panel_is_the_one_the_chip_names(self, anomaly_rows):
        chip = next(c for c in asking.CHIPS
                    if c.question == 'At which stage do the errors sit?')
        opened = asking.click(chip, anomaly_rows).panels
        assert [p.name for p in opened] == ['by_stage']

    def test_no_chip_opens_more_than_one(self, anomaly_rows):
        for chip in asking.CHIPS:
            assert len(asking.click(chip, anomaly_rows).panels) <= 1

    def test_an_empty_filter_still_refuses(self):
        assert asking.click(asking.CHIPS[0], []).refusal


class TestATypedQuestion:

    #: What the router asks the model for, and gets back.
    ROUTE = '{"panels": ["by_stage", "by_check", "flagged_by_supplier"]}'

    def test_a_count_question_opens_no_panel(self, anomaly_rows, fake_model):
        model = fake_model(self.ROUTE, 'Most flags sit in purchasing.')
        given = asking.answer('How many were flagged?', anomaly_rows,
                              model=model)
        assert given.panels == []

    def test_it_still_answers_with_no_panel(self, anomaly_rows, fake_model):
        model = fake_model(self.ROUTE, 'Most flags sit in purchasing.')
        given = asking.answer('How many were flagged?', anomaly_rows,
                              model=model)
        assert given.sentence

    def test_a_breakdown_question_opens_one(self, anomaly_rows, fake_model):
        model = fake_model(self.ROUTE, 'Most flags sit in purchasing.')
        given = asking.answer('Show the flags by stage', anomaly_rows,
                              model=model)
        assert len(given.panels) == 1

    def test_the_panel_is_the_router_s_first_pick(self, anomaly_rows,
                                                  fake_model):
        model = fake_model(self.ROUTE, 'Most flags sit in purchasing.')
        given = asking.answer('Show the flags by stage', anomaly_rows,
                              model=model)
        assert given.panels[0].name == 'by_stage'
