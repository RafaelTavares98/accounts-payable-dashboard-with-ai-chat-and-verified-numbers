"""One question on the anomaly view, from the click to the sentence.

The same order as the cost assistant: the model names panels off the
anomaly menu, code computes every figure, and only then is the model
handed those figures to write one sentence. A sentence carrying a number
nobody computed is replaced by one written by code.

`ours` is how many documents the reader left for a person, from the cost
report. It travels beside the scored rows, because the checking model
never sees a document nobody could read.
"""

import anomalies
import anomaly_panels
import plot_answers
import routing
from answering import Answer, _computed_values, _invented_numbers, _NUMBER


def _opened(question, names):
    """The panels a question is allowed to open: one, and none when the
    answer is a single figure. A sentence does not need a picture beside
    it, and three pictures bury the dashboard underneath them."""
    if not names or not plot_answers.wants_a_plot(question):
        return []
    return list(names)[:1]


def _money(value):
    return f'{value:,.2f}'


def brief(scored, ours=0):
    """Everything true about the rows on screen, as text the model reads."""
    lines = [
        f'Reviewed: {anomalies.reviewed(scored)} invoices. '
        f'Flagged: {anomalies.flagged_count(scored)}, '
        f'{_money(anomalies.flagged_total(scored))} in all, '
        f'{anomalies.flag_rate(scored)}% of those reviewed.',
        'Whose error: ' + ', '.join(
            f'{label} {count}'
            for label, count in anomalies.by_origin(scored, ours=ours)),
        'Flags by stage: ' + ', '.join(
            f'{stage} {count} invoices {_money(amount)}'
            for stage, count, amount in anomalies.by_stage(scored)),
        'Flags by check: ' + ', '.join(
            f'{check} {count}' for check, count in anomalies.by_check(scored)),
        'Flags by supplier: ' + ', '.join(
            f'{who} {count}' for who, count, _ in anomalies.by_supplier(scored)[:6]),
        'Flags by week: ' + ', '.join(
            f'{week} {flagged} of {total}, {_money(amount)}'
            for week, flagged, total, amount in anomalies.by_week(scored)[-12:]),
        'Highest scores: ' + ', '.join(
            f'{row.number} ({row.supplier}, {row.check}, {_money(row.total)})'
            for row in anomalies.worst(scored, 5)),
    ]
    return '\n'.join(lines)


def _headline(scored):
    return (f'{anomalies.flagged_count(scored)} of '
            f'{anomalies.reviewed(scored)} invoices were flagged, '
            f'{_money(anomalies.flagged_total(scored))} in all.')


def _top(panel, opening):
    if not panel.rows:
        return 'Nothing is flagged in the current filter.'
    label, value = panel.rows[0]
    return f'{opening} {label}, with {value}.'


def _origin(scored, ours):
    return (f'{anomalies.client_errors(scored)} client errors were '
            f'confirmed and {ours} of ours went to a person.')


def _code_sentence(built, scored, ours=0):
    """Written by code, so it can only carry computed figures."""
    for panel in built:
        if panel.name == 'flags':
            return _headline(scored)
        if panel.name == 'by_origin':
            return _origin(scored, ours)
        if panel.name == 'by_stage':
            return _top(panel, 'Most flags sit in')
        if panel.name == 'by_check':
            return _top(panel, 'The check that finds the most is')
        if panel.name == 'flagged_by_supplier':
            return _top(panel, 'The supplier with the most flags is')
        if panel.name == 'worst_flags' and panel.rows:
            return f'The first to check is {panel.rows[0][0]}.'
    return _headline(scored)


def _chat(question, scored, today, model, history):
    prompt = (
        routing._said_before(history) +
        'You are the assistant beside a dashboard of invoices a checking '
        'model flagged as possible errors. Reply in one or two short '
        'sentences, in English. Do not state any number at all. If it '
        'fits, say what can be asked: how many were flagged, whose error, '
        'at which stage, by which check, from which supplier.\n'
        f'Person: {question}'
    )
    try:
        said = model(prompt)
    except Exception:
        said = ''
    if not said or _invented_numbers(said, set()):
        said = ('Ask how many invoices were flagged, whose error they are, '
                'at which stage, by which check, or from which supplier.')
    return Answer(sentence=said.strip(), rows_used=len(scored), as_of=today)


def _sentence_prompt(question, built, digest):
    listed = '; '.join(f'{panel.title}: ' + ', '.join(
        f'{label} {value}' for label, value in panel.rows[:6])
        for panel in built)
    return (
        'This is what the person is looking at:\n'
        f'{routing._what_is_on_screen(anomaly_panels.BOARD)}\n\n'
        'Everything true about those rows, computed by code:\n'
        f'{digest}\n\n'
        f'The panels now open show: {listed}.\n\n'
        f'The question was: {question}\n'
        'Answer it in one or two short sentences. An anomaly here is an '
        'error at one stage of the process. Use only the figures given: '
        'any other number would be invented. Do not apologise and do not '
        'describe the panels. Use commas for thousands and a dot for '
        'decimals.'
    )


def answer(question, scored, today=None, model=None, history=None, ours=0):
    """One question, two model calls, no invented figure."""
    if not scored:
        return Answer(rows_used=0, as_of=today,
                      refusal='Nothing matches the current filter.')
    routed = routing.route(question, model=model, history=history,
                           board=anomaly_panels.BOARD)
    if routed.small_talk:
        return _chat(question, scored, today, model, history)
    if routed.refusal:
        return Answer(rows_used=len(scored), as_of=today,
                      refusal=routed.refusal)

    named = routed.panels
    built = [anomaly_panels.build(name, scored, ours=ours)
             for name in _opened(question, named)]
    # The sentence is written over what the question asked about, even
    # when no panel is opened for it.
    spoken = [anomaly_panels.build(name, scored, ours=ours)
              for name in list(named)[:1]]
    digest = brief(scored, ours=ours)
    try:
        sentence = model(_sentence_prompt(question, spoken, digest))
    except Exception:
        return Answer(panels=built,
                      sentence=_code_sentence(spoken, scored, ours),
                      rejected=True, rows_used=len(scored), as_of=today)

    allowed = _computed_values([], spoken)
    allowed |= set(_NUMBER.findall(digest))
    allowed |= {token.replace(',', '') for token in _NUMBER.findall(digest)}
    allowed |= {token.rstrip('.,').replace(',', '')
                for token in _NUMBER.findall(digest)}
    if _invented_numbers(sentence, allowed):
        return Answer(panels=built,
                      sentence=_code_sentence(spoken, scored, ours),
                      rejected=True, rows_used=len(scored), as_of=today)
    return Answer(panels=built, sentence=sentence.strip(), rejected=False,
                  rows_used=len(scored), as_of=today)


class Chip:
    """One ready-made question, with the panels it opens."""

    def __init__(self, question, panel_names):
        self.question = question
        self.panels = panel_names


CHIPS = [
    Chip('How many invoices were flagged?', ['flags']),
    Chip('Whose errors are they?', ['by_origin']),
    Chip('At which stage do the errors sit?', ['by_stage']),
    Chip('Which check finds the most?', ['by_check']),
    Chip('Which invoices should be checked first?', ['worst_flags']),
]


def click(chip, scored, today=None, ours=0):
    """One chip, no model call, one sentence written by code."""
    if not scored:
        return Answer(rows_used=0, as_of=today,
                      refusal='Nothing matches the current filter.')
    built = [anomaly_panels.build(name, scored, ours=ours)
             for name in _opened(chip.question, chip.panels)]
    lead = [anomaly_panels.build(chip.panels[0], scored, ours=ours)]
    return Answer(panels=built, sentence=_code_sentence(lead, scored, ours),
                  rejected=False, rows_used=len(scored), as_of=today)
