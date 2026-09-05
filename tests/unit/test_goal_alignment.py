import json

import pytest

from src.models import BookCandidate, LearningGoal, UserProfile
from src.services.goal_alignment import exclusion_conflict
from src.services.recommendation import (
    ROLES,
    _select_complementary,
    build_queries,
    load_demo_candidates,
)
from src.services.scoring import assess_book


@pytest.mark.parametrize('purpose,title', [
    ('用 Python 和 scikit-learn 做分类，不要 MATLAB，不需要金融营销或泛泛的AI趋势读物。', 'MATLAB机器学习'),
    ('用 Python 和 scikit-learn 做分类，不要 MATLAB，不需要金融营销或泛泛的AI趋势读物。', '金融大数据研究与应用'),
    ('Use Python. No MATLAB or finance books.', 'MATLAB Machine Learning'),
    ('Use Python. No MATLAB or finance books.', 'Machine Learning in Finance'),
])
def test_explicit_exclusions_cannot_be_overridden_by_keyword_score(purpose, title):
    goal = LearningGoal(topic='Machine learning', purpose=purpose, duration_weeks=6, hours_per_week=4)
    book = BookCandidate(canonical_id='bad', title=title, authors=['Author'], language='en',
                         description='Machine learning fundamentals theory evaluation applications research methods', search_roles=list(ROLES))
    assert exclusion_conflict(book, goal)
    assert assess_book(book, goal, UserProfile(education_level='beginner'), ROLES[0]).goal_relevance == 0
    assert not _select_complementary([book], goal, UserProfile(education_level='beginner'))[0]


def test_avoid_leakage_is_a_learning_objective_not_an_excluded_book_subject():
    goal = LearningGoal(topic='Machine learning', purpose='Learn how to avoid data leakage.', duration_weeks=6, hours_per_week=4)
    assert not exclusion_conflict(BookCandidate(canonical_id='good', title='Avoiding data leakage', authors=['Author']), goal)


class Selector:
    def __init__(self, mode):
        self.mode = mode

    def generate_structured(self, system, user, output_model):
        pools = json.loads(user)['candidates_by_role']
        ids = [pool[0]['id'] for pool in pools.values()]
        return output_model(requirements_met=self.mode == 'complete', gaps='A suitable application is missing.',
            foundation_id='invented' if self.mode == 'invented' else ids[0], foundation_reason='Conceptual grounding.',
            application_id='' if self.mode == 'partial' else ids[1], application_reason='Engineering mechanisms.',
            perspective_id=ids[2], perspective_reason='Ethical analysis.')


@pytest.mark.parametrize('mode,count', [('complete', 3), ('partial', 2), ('invented', 2)])
def test_semantic_gate_validates_ids_and_allows_partial_paths(mode, count):
    goal = LearningGoal(topic='Embodied Intelligence', purpose='Learn', duration_weeks=6, hours_per_week=4)
    selected, assessments, warnings = _select_complementary(load_demo_candidates(), goal,
        UserProfile(education_level='undergraduate'), Selector(mode))
    assert len(selected) == count
    if mode != 'complete':
        assert warnings
    if mode == 'partial':
        assert assessments[-1].evaluated_role == ROLES[2]
        assert not assessments[-1].meets_stated_requirements


def test_goal_specific_queries_override_generic_topic_queries():
    goal = LearningGoal(topic='机器学习', purpose='科研分类', duration_weeks=6, hours_per_week=4,
                        catalog_queries={ROLES[1]: '机器学习 scikit-learn'})
    assert build_queries(goal, 'zh')[ROLES[1]] == '机器学习 scikit-learn'
