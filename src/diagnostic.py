from __future__ import annotations

import hashlib
import json
import re

from src.language import interface_language
from src.models import (
    BookCandidate,
    ConceptMastery,
    DiagnosticQuestion,
    LearningGoal,
    ReadingStage,
    UserProfile,
)


def diagnostic_scope_key(
    goal: LearningGoal,
    profile: UserProfile,
    book: BookCandidate | None = None,
    stage: ReadingStage | None = None,
) -> str:
    """Identify the exact learning context that owns one knowledge check."""
    payload = {
        "language": interface_language(goal),
        "topic": goal.topic.strip().casefold(),
        "purpose": goal.purpose.strip().casefold(),
        "focus_details": getattr(goal, "focus_details", "").strip().casefold(),
        "difficulty": goal.preferred_difficulty,
        "education_level": profile.education_level,
        "background": sorted(item.strip().casefold() for item in profile.background_knowledge),
        "major": (profile.major or "").strip().casefold(),
        "book_id": book.canonical_id.strip() if book else "",
        "stage_number": stage.stage_number if stage else 0,
        "stage_objective": stage.learning_objective.strip().casefold() if stage else "",
        "stage_concepts": [item.strip().casefold() for item in stage.concepts] if stage else [],
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]


def build_diagnostic(
    goal: LearningGoal,
    profile: UserProfile,
    book: BookCandidate | None = None,
    stage: ReadingStage | None = None,
) -> list[DiagnosticQuestion]:
    """Build questions for the current goal, book, and reading stage."""
    chinese = interface_language(goal) == "zh"
    book_title = book.title if book else ("当前阶段材料" if chinese else "the current reading")
    stage_concepts = [item.strip() for item in (stage.concepts if stage else []) if item.strip()]
    primary_concept = stage_concepts[0] if stage_concepts else goal.topic
    secondary_concept = (
        stage_concepts[1]
        if len(stage_concepts) > 1
        else ("方法与应用" if chinese else "methods and application")
    )
    embodied_topic = "具身" in goal.topic or "embodied" in goal.topic.casefold()
    if chinese:
        primary_signals = (
            ["身体", "环境", "感知", "交互"]
            if embodied_topic
            else [primary_concept, goal.topic, "因为", "关系"]
        )
        application_signals = (
            ["反馈", "传感器", "行动", "更新"]
            if embodied_topic
            else [secondary_concept, "步骤", "应用", "例子"]
        )
        return [
            DiagnosticQuestion(
                concept=primary_concept,
                prompt=(
                    f"结合《{book_title}》，请用自己的话解释“{primary_concept}”，"
                    f"并说明它与学习目标“{goal.topic}”的关系。"
                ),
                expected_signals=primary_signals,
            ),
            DiagnosticQuestion(
                concept=secondary_concept,
                prompt=(
                    f"从《{book_title}》选一个方法或案例，说明“{secondary_concept}”"
                    f"可以怎样用于“{goal.purpose}”。请给出步骤或具体例子。"
                ),
                expected_signals=application_signals,
            ),
            DiagnosticQuestion(
                concept="证据与边界",
                prompt=(
                    f"从《{book_title}》选择一个重要观点：它的依据是什么、适用于什么条件，"
                    "又有哪些限制？如果还不确定，也可以明确写出疑问。"
                ),
                expected_signals=["依据", "条件", "限制", "证据"],
            ),
        ]
    primary_signals = (
        ["body", "environment", "sensorimotor", "interaction"]
        if embodied_topic
        else [primary_concept.casefold(), goal.topic.casefold(), "because", "relationship"]
    )
    application_signals = (
        ["feedback", "sensor", "action", "update"]
        if embodied_topic
        else [secondary_concept.casefold(), "step", "apply", "example"]
    )
    return [
        DiagnosticQuestion(
            concept=primary_concept,
            prompt=(
                f'Using “{book_title}”, explain “{primary_concept}” in your own words '
                f'and connect it to your goal of learning “{goal.topic}”.'
            ),
            expected_signals=primary_signals,
        ),
        DiagnosticQuestion(
            concept=secondary_concept,
            prompt=(
                f'Choose one method or example from “{book_title}”. How could “{secondary_concept}” '
                f'be used for “{goal.purpose}”? Include concrete steps or an example.'
            ),
            expected_signals=application_signals,
        ),
        DiagnosticQuestion(
            concept="evidence and limits",
            prompt=(
                f'Choose one important claim from “{book_title}”. What supports it, when does it apply, '
                "and what are its limits? State any remaining uncertainty clearly."
            ),
            expected_signals=["evidence", "condition", "limit", "because"],
        ),
    ]


def build_mixed_diagnostic(
    goal: LearningGoal, profile: UserProfile, book: BookCandidate | None = None,
    stage: ReadingStage | None = None,
) -> list[DiagnosticQuestion]:
    """A labeled, self-contained fallback; never claims access to book chapters.

    Local items test foundational reasoning in supported subjects. They are not
    presented as a model-generated assessment of a narrowly specified syllabus.
    """
    chinese = interface_language(goal) == "zh"
    scope = " ".join([goal.topic, getattr(goal, "focus_details", ""),
                      stage.learning_objective if stage else ""]).casefold()
    psychology = any(word in scope for word in ("心理", "认知", "psycholog", "cognitive"))
    machine_learning = any(word in scope for word in ("机器学习", "深度学习", "machine learning", "deep learning"))
    if psychology:
        if chinese:
            items = (
                ("相关与因果", "一项观察研究发现，睡眠更少的学生压力得分更高。仅凭这个结果，哪项结论成立？",
                 ["睡眠不足一定会导致压力上升", "这批学生的睡眠时长与压力得分存在关联", "减轻压力一定能延长睡眠", "睡眠和压力之间不存在其他影响因素"], 1,
                 "观察到的是关联。压力也可能影响睡眠，课程负担等因素还可能同时影响两者；不能仅凭相关确定因果方向。"),
                ("信度与效度", "判断：某心理量表在相同条件下重复测量的结果很稳定，因此已经证明它测到了声称测量的心理特征。", False,
                 "稳定性支持信度，但不充分证明效度。一个稳定偏离目标的量表也可能很可靠；还需与目标构念相关的证据。"),
                ("研究设计", "研究者让学生自愿选择参加记忆训练，发现参加者测试成绩更高。请指出一个不能直接把差异归因于训练的原因，并提出一个改进办法。",
                 "可指出原有能力、动机等自我选择差异；提出随机分组并保持测试条件一致等改进。需解释该改进如何减少一种混淆，不要求认定训练无效。"),
            )
        else:
            items = (
                ("Correlation and causation", "An observational study finds that students who sleep less have higher stress scores. Which conclusion follows from this result alone?",
                 ["Less sleep necessarily causes higher stress", "Sleep duration and stress scores are associated in this sample", "Reducing stress necessarily increases sleep", "No other factor influences both sleep and stress"], 1,
                 "The result establishes an association, not its direction or cause. Stress may affect sleep, and factors such as workload may affect both."),
                ("Reliability and validity", "True or false: A psychological scale gives stable results under the same conditions, so this alone proves that it measures the psychological trait it claims to measure.", False,
                 "Consistency supports reliability, not validity by itself. A measure can be consistently off target; evidence connecting it to the intended construct is still needed."),
                ("Research design", "Students choose whether to join memory training. Participants later score higher. Give one reason this difference cannot be attributed to training alone and one design improvement.",
                 "Identify selection differences such as prior ability or motivation, then explain how a change such as random assignment with consistent testing addresses a confound. Do not infer that the training is ineffective."),
            )
    elif machine_learning:
        if chinese:
            items = (
                ("数据泄漏", "已划分训练集和测试集，需要用均值、标准差标准化特征。哪种流程能避免测试集信息参与拟合？",
                 ["合并两组数据拟合，再分别变换", "分别在训练集和测试集拟合各自的标准化器", "只在训练集拟合，用同一个标准化器变换两组数据", "先在测试集拟合，再变换训练集"], 2,
                 "只用训练集估计参数，再把同一变换用于测试集。测试数据不参与拟合，且两组数据使用一致的特征坐标；泄漏可能使评估有偏，但不保证分数必然上升。"),
                ("泛化评估", "判断：某分类器在训练集上准确率达到 99%，仅凭这一数字就能确定它对新样本也有很好的预测能力。", False,
                 "训练集成绩不能单独证明泛化能力。还需在未参与拟合或调参、且与应用场景相符的数据上评估；高训练准确率本身也不能证明过拟合。"),
                ("类别不平衡", "一个测试集有 100 个样本，其中 95 个是负类。模型把所有样本都预测为负类，准确率为 95%。它能识别正类吗？请说明理由。",
                 "不能识别正类：5 个正类全部漏掉，正类召回率为 0。95% 准确率被多数类支配，不代表正类识别能力；不要求推断训练是否过拟合。"),
            )
        else:
            items = (
                ("Data leakage", "Training and test sets are already separate. Features need mean/standard-deviation scaling. Which workflow keeps test information out of fitting?",
                 ["Fit on the combined sets, then transform each", "Fit a separate scaler on each set", "Fit on training data only, then transform both with that same scaler", "Fit on test data, then transform training data"], 2,
                 "Estimate scaling parameters using training data only and apply the same transform to both sets. This avoids test-informed fitting and keeps coordinates consistent. Leakage can bias evaluation; it need not increase every score."),
                ("Generalization", "True or false: A classifier has 99% training accuracy. This number alone establishes that it predicts new samples well.", False,
                 "Training performance alone establishes neither generalization nor overfitting. Evaluate on relevant unseen data that was not used for fitting or model selection."),
                ("Class imbalance", "A test set has 100 samples, including 95 negatives. A model predicts negative for every sample and scores 95% accuracy. Can it identify the positives? Explain briefly.",
                 "No: it misses all five positives, so positive-class recall is zero. Majority-class prevalence explains the high accuracy; this result alone does not diagnose overfitting."),
            )
    elif chinese:
        items = (
            ("比较解释", f"学习“{goal.topic}”时，两个解释都能说明同一个现象。哪种后续做法最能帮助区分它们？",
             ["选择表述更复杂的解释", "只寻找支持原来想法的材料", "比较赞同两种解释的人数", "找出两种解释预测不同的情形，再核对证据"], 3,
             "现有现象同时符合两种解释，还不能区分它们。比较产生不同预测的情形及证据更有帮助；复杂程度和赞同人数都不能单独决定解释是否成立。"),
            ("结论边界", "判断：有人声称某方法对所有情形都有效；只要找到一个可靠的反例，就足以否定这个没有例外的说法。", True,
             "“所有情形都有效”是全称断言，一个符合讨论范围的可靠反例即可否定它；这不意味着该方法在其他条件下也无效。"),
            ("应用与限制", f"围绕你想学的“{goal.topic}”，选一个已经接触的概念，举一个具体应用例子，并指出这个例子不能说明什么。",
             "判断概念与例子是否准确对应，是否给出具体情形，并区分例子支持的结论与不能推出的结论。未知的书中表述不作为评分依据。"),
        )
    else:
        items = (
            ("Comparing explanations", f"While studying {goal.topic}, two explanations fit the same observation. Which next step best helps distinguish them?",
             ["Choose the explanation with more complex wording", "Seek only evidence for your original view", "Count how many people support each explanation", "Find a case where their predictions differ and check the evidence"], 3,
             "An observation compatible with both explanations does not distinguish them. Evidence about divergent predictions is more informative than complexity, popularity or selective confirmation."),
            ("Limits of a claim", "True or false: A method is claimed to work in every case without exception. One reliable counterexample within the claimed scope is enough to refute that universal claim.", True,
             "One valid counterexample refutes a universal claim. It does not establish that the method fails under all other conditions."),
            ("Application and limits", f"Choose one concept you have encountered while studying {goal.topic}. Give a concrete application and explain one conclusion that this example does not establish.",
             "Assess whether the example accurately uses the concept, specifies a concrete situation and distinguishes supported conclusions from overclaims. Do not invent book passages as grading evidence."),
        )
    choice, judgment, short = items
    labels = ["正确", "错误"] if chinese else ["True", "False"]
    return [
        DiagnosticQuestion(concept=choice[0], prompt=choice[1], question_type="single_choice",
                           options=choice[2], correct_answer=choice[2][choice[3]], explanation=choice[4],
                           generation_source="local"),
        DiagnosticQuestion(concept=judgment[0], prompt=judgment[1], question_type="true_false",
                           options=labels, correct_answer=labels[0 if judgment[2] else 1],
                           explanation=judgment[3], generation_source="local"),
        DiagnosticQuestion(concept=short[0], prompt=short[1], rubric=short[2], generation_source="local"),
    ]


def score_diagnostic(
    questions: list[DiagnosticQuestion], answers: list[str], skipped: bool = False
) -> list[ConceptMastery]:
    """Estimate understanding from concepts and the reasoning shown in an answer.

    This stays transparent and deterministic, but avoids treating a technically
    sound answer as empty merely because it does not repeat a generic label.
    """

    def is_chinese(text: str) -> bool:
        return any("\u4e00" <= char <= "\u9fff" for char in text)

    def content_units(text: str, chinese: bool) -> int:
        if chinese:
            return len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text))
        return len(re.findall(r"[A-Za-z0-9]+", text))

    def reasoning_signals(question: DiagnosticQuestion, chinese: bool) -> list[str]:
        prompt = question.prompt.casefold()
        concept = question.concept.casefold()
        if ("依据" in prompt and "限制" in prompt) or "evidence and limits" in concept:
            return (
                ["依据", "证据", "条件", "限制", "局限", "依赖", "误差", "失效", "不适用", "但", "然而"]
                if chinese
                else ["evidence", "support", "condition", "limit", "depend", "error", "fail", "unless", "however", "but"]
            )
        if ("步骤" in prompt or "例子" in prompt) or ("step" in prompt or "example" in prompt):
            return (
                ["例如", "比如", "步骤", "首先", "然后", "再", "传感器", "融合", "定位", "地图", "规划", "控制", "反馈", "应用"]
                if chinese
                else ["example", "for instance", "step", "first", "then", "sensor", "fusion", "localization", "map", "planning", "control", "feedback", "apply"]
            )
        return (
            ["因为", "因此", "关系", "意味着", "通过", "感知", "环境", "交互", "反馈", "行动", "定位", "规划", "控制"]
            if chinese
            else ["because", "therefore", "relationship", "means", "through", "perception", "environment", "interaction", "feedback", "action", "localization", "planning", "control"]
        )

    mastery: list[ConceptMastery] = []
    for index, question in enumerate(questions):
        answer = answers[index] if index < len(answers) else ""
        chinese = is_chinese(question.prompt)
        if question.question_type != "short_answer":
            answered = not skipped and answer.strip() in question.options
            correct = answered and answer.strip() == question.correct_answer
            evidence = (("回答正确。" if correct else "这次选项不正确。") + question.explanation
                        if answered else ("本题未作答，尚不能判断理解情况。" if chinese else
                                          "Not answered; understanding has not been assessed."))
            if answered and not chinese:
                evidence = ("Correct. " if correct else "Incorrect choice. ") + question.explanation
            mastery.append(ConceptMastery(concept=question.concept,
                                          mastery_score=1.0 if correct else 0.0,
                                          confidence=0.5 if answered else 0.0,
                                          evidence=[evidence]))
            continue
        normalized = " ".join(answer.casefold().split())
        hits = sum(signal in normalized for signal in question.expected_signals)
        reasoning_hits = sum(
            signal in normalized for signal in reasoning_signals(question, chinese)
        )
        units = content_units(normalized, chinese)
        if not normalized:
            score = 0.0
        elif units < (12 if chinese else 5):
            score = min(0.25, 0.08 + (0.08 * hits) + (0.04 * reasoning_hits))
        else:
            direct_coverage = min(1.0, hits / 2)
            reasoning_coverage = min(1.0, reasoning_hits / 3)
            substance = min(1.0, units / (48 if chinese else 24))
            score = min(
                1.0,
                0.08
                + (0.42 * direct_coverage)
                + (0.35 * reasoning_coverage)
                + (0.15 * substance),
            )
        confidence = (
            0.25
            if skipped
            else min(
                0.9,
                0.42
                + (min(units, 60) / 125)
                + min(hits + reasoning_hits, 4) * 0.03,
            )
        )
        if chinese:
            evidence = f"回答命中 {hits} 个核心概念，并呈现 {reasoning_hits} 个解释、应用或边界线索。"
        else:
            evidence = f"The answer matched {hits} core concepts and showed {reasoning_hits} explanation, application, or boundary signals."
        mastery.append(
            ConceptMastery(
                concept=question.concept,
                mastery_score=0.25 if skipped else round(score, 2),
                confidence=round(confidence, 2),
                evidence=["已跳过诊断，采用保守基线。" if chinese else "Knowledge check skipped; a conservative starting point was used."]
                if skipped
                else [evidence],
            )
        )
    return mastery
