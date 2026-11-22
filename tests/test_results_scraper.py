from selectolax.parser import HTMLParser

from cubingrf_notifier.results.cubingrf import CubingRFResultsScraper


RESULT_PAGE = """
<html><body>
<div class="result-entry bg-green-300" data-registrant-id="49">
  <div class="w-fit mr-2 xl:w-12 xl:mr-0"><b>1</b></div>
  <a href="/results/persons/49">Name</a>
  <div data-attempt-number="1" data-raw-result="912">9.12</div>
  <div data-attempt-number="2" data-raw-result="888">8.88</div>
  <div data-attempt-number="3" data-raw-result="845">8.45</div>
  <div data-attempt-number="4" data-raw-result="930">9.30</div>
  <div data-attempt-number="5" data-raw-result="855">8.55</div>
  <span class="font-bold">8.86</span>
</div>
<div class="result-entry" data-registrant-id="50">
  <div class="w-fit mr-2 xl:w-12 xl:mr-0"><b>2</b></div>
  <a href="/results/persons/50">Name2</a>
  <div data-attempt-number="1" data-raw-result="-1">DNF</div>
  <div data-attempt-number="2" data-raw-result="900">9.00</div>
  <div data-attempt-number="3" data-raw-result="900">9.00</div>
  <div data-attempt-number="4" data-raw-result="900">9.00</div>
  <div data-attempt-number="5" data-raw-result="900">9.00</div>
  <span class="font-bold">9.00</span>
</div>
</body></html>
"""


def test_parse_results_extracts_fields():
    results = CubingRFResultsScraper()._parse_results(RESULT_PAGE)
    assert len(results) == 2

    first = results[0]
    assert first.registrant_id == 49
    assert first.place == 1
    assert first.attempts == (912, 888, 845, 930, 855)
    assert first.average == 886  # "8.86" seconds -> 886 centiseconds
    assert first.best == 845      # fastest non-DNF attempt
    assert first.advanced is True

    second = results[1]
    assert second.registrant_id == 50
    assert second.advanced is False
    assert second.best == 900  # DNF (-1) ignored for best


MINUTE_AVG_PAGE = """
<html><body>
<div class="result-entry" data-registrant-id="12">
  <div class="w-fit mr-2 xl:w-12 xl:mr-0"><b>14</b></div>
  <a href="/results/persons/12">Name</a>
  <div data-attempt-number="1" data-raw-result="10613">1:46.13</div>
  <div data-attempt-number="2" data-raw-result="11056">1:50.56</div>
  <div data-attempt-number="3" data-raw-result="9236">1:32.36</div>
  <div data-attempt-number="4" data-raw-result="8869">1:28.69</div>
  <div data-attempt-number="5" data-raw-result="9626">1:36.26</div>
  <span class="font-bold">1:38.25</span>
</div>
</body></html>
"""


def test_parse_average_over_one_minute():
    results = CubingRFResultsScraper()._parse_results(MINUTE_AVG_PAGE)
    assert len(results) == 1
    # Average >= 1 minute is spelled on the page as 'M:SS.CC'; it must parse
    # to centiseconds just like the under-a-minute 'SS.CC' spelling.
    assert results[0].average == 9825


DNF_AVG_PAGE = """
<html><body>
<div class="result-entry" data-registrant-id="40">
  <div class="w-fit mr-2 xl:w-12 xl:mr-0"><b>16</b></div>
  <a href="/results/persons/40">Name</a>
  <div data-attempt-number="1" data-raw-result="-1">DNF</div>
  <div data-attempt-number="2" data-raw-result="-1">DNF</div>
  <div data-attempt-number="3" data-raw-result="-2">DNS</div>
  <div data-attempt-number="4" data-raw-result="8785">1:27.85</div>
  <div data-attempt-number="5" data-raw-result="9504">1:35.04</div>
  <span class="font-bold">DNF</span>
</div>
</body></html>
"""


def test_parse_average_dnf_token():
    results = CubingRFResultsScraper()._parse_results(DNF_AVG_PAGE)
    assert len(results) == 1
    # A DNF average is spelled as the plain token 'DNF'; it stays DNF (-1)
    # rather than being dropped (which used to hide the "average" line).
    assert results[0].average == -1
    assert results[0].best == 8785  # non-DNF/DNS attempts only


COMPETITORS_PAGE = """
<html><body>
<table>
  <tr><td>1</td><td><a href="/persons/AS03">Ivan Ivanov</a></td><td>ID: 49</td></tr>
  <tr><td>2</td><td><a href="/persons/AG32">Petr Petrov</a></td><td>ID: 50</td></tr>
</table>
</body></html>
"""


def test_person_paths_maps_rsf_to_registrant_id():
    scraper = CubingRFResultsScraper()
    mapping = scraper._person_paths(HTMLParser(COMPETITORS_PAGE))
    assert mapping == {"AS03": 49, "AG32": 50}


ROSTER_PAGE = """
<html><body>
<table>
  <tr><td><a href="/persons/AS03">Ivan</a></td></tr>
  <tr><td><a href="/persons/AG32">Petr</a></td></tr>
  <tr><td><a href="/persons/AK52">Sid</a></td></tr>
</table>
</body></html>
"""


def test_parse_roster_counts_participants():
    scraper = CubingRFResultsScraper()
    roster = scraper._parse_roster(ROSTER_PAGE)
    assert roster.count == 3
    assert roster.registrant_ids == ()


def test_parse_roster_maps_to_registrant_ids():
    scraper = CubingRFResultsScraper()
    mapping = {"AS03": 49, "AG32": 50, "AK52": 99}
    roster = scraper._parse_roster(ROSTER_PAGE, mapping=mapping)
    assert roster.count == 3
    assert roster.registrant_ids == (49, 50, 99)


SCHEDULE_PAGE = """
<html><body>
<div id="tabs-rounds">
  <div data-event="333" data-round="1"><h4>1-й раунд</h4></div>
  <div data-event="333" data-round="2"><h4>Финал</h4></div>
  <div data-event="222" data-round="1"><h4>1-й раунд</h4></div>
  <div data-event="333fm" data-round="1"><h4>Финал</h4></div>
</div>
<div id="tabs-schedule">
  <h3>Воскресенье, 22 ноября</h3>
  <div class="border border-gray-300 p-3 rounded">
    <div class="text-sm font-bold">09:30 — 10:30</div>
    <div class="text-lg font-bold">3x3x3, 1-й раунд</div>
    <a class="text-gray-700 underline" href="https://cubingrf.org/competitions/X/results/333/1">Результаты</a>
    <a class="text-gray-700 underline" href="https://cubingrf.org/competitions/X/groups/333/1">Группы</a>
  </div>
  <div class="border border-gray-300 p-3 rounded">
    <div class="text-sm font-bold">10:40 — 10:50</div>
    <div class="text-lg font-bold">Инструктаж</div>
  </div>
  <div class="border border-gray-300 p-3 rounded">
    <div class="text-sm font-bold">11:40 — 12:40</div>
    <div class="text-lg font-bold">Мегаминкс, 1-й раунд</div>
    <a class="text-gray-700 underline" href="https://cubingrf.org/competitions/X/results/minx/1">Результаты</a>
  </div>
  <div class="border border-gray-300 p-3 rounded">
    <div class="text-sm font-bold">14:40 — 15:50</div>
    <div class="text-lg font-bold">Square-1, 1-й раунд</div>
    <a class="text-gray-700 underline" href="https://cubingrf.org/competitions/X/results/sq1/1">Результаты</a>
    <a class="text-gray-700 underline" href="https://cubingrf.org/competitions/X/results/sq1/1">Ещё раз</a>
  </div>
  <div class="border border-gray-300 p-3 rounded">
    <div class="text-sm font-bold">16:00 — 16:30</div>
    <i class="cubing-icon event-333"></i>
    <div class="text-lg font-bold">Кубик 3x3x3, Финал</div>
  </div>
  <div class="border border-gray-300 p-3 rounded">
    <div class="text-sm font-bold">16:00 — 17:00</div>
    <div class="text-lg font-bold">Рекорды</div>
    <a href="https://cubingrf.org/competitions/X/results/333/psychSheet">Предварительный рейтинг</a>
  </div>
  <h3>Воскресенье, 22 ноября</h3>
  <div class="border border-gray-300 p-3 rounded">
    <div class="text-sm font-bold">10:00 — 11:00</div>
    <div class="text-lg font-bold">2x2x2, 1-й раунд</div>
    <a href="https://cubingrf.org/competitions/X/results/222/1">Результаты</a>
  </div>
  <div class="border border-gray-300 p-3 rounded">
    <div class="text-sm font-bold">08:30 — 09:00</div>
    <i class="cubing-icon event-333fm"></i>
    <div class="text-lg font-bold">3x3x3 на количество ходов, Финал</div>
  </div>
</div>
</body></html>
"""


def test_parse_schedule_sorts_parallel_halls_by_start_time():
    scraper = CubingRFResultsScraper()
    # DOM order is hall 1 (09:30 … 16:00) then hall 2 (10:00, 08:30), but the
    # schedule order must be chronological across both halls.
    assert scraper._parse_schedule(SCHEDULE_PAGE) == [
        ("333fm", 1),
        ("333", 1),
        ("222", 1),
        ("minx", 1),
        ("sq1", 1),
        ("333", 2),
    ]


def test_parse_schedule_missing_tab_returns_empty():
    scraper = CubingRFResultsScraper()
    assert scraper._parse_schedule("<html><body></body></html>") == []