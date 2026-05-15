# ----- recommendation precision evaluation @ backend/eval/eval_precision.py -----
"""
Eval 2 - AI Precision (LLM-as-a-Judge) Evaluation

Measures semantic usefulness of internal-link recommendations using a Groq-hosted
LLM judge. The evaluator runs a fixed draft suite through the API, then asks the
judge whether each suggested link is semantically accurate and highly helpful.

Target: >90% YES rate overall, including strong performance on ambiguity tripwire
cases such as Apple/fruit vs Apple/company and Python/snake vs Python/language.
"""

import json
import os

import httpx
import requests

from backend.utils.config import config
from backend.utils.logger import logger

API_BASE = os.environ.get("EVAL_API_URL", "http://localhost:8000/api/v1")
NUM_DRAFTS = 50

evaluation_cases = [
    {
        "text": "When we finally achieve Artificial General Intelligence, the timeline might accelerate much faster than we anticipate.",
        "tripwire": False,
    },
    {
        "text": "The jump from human-level AI to Artificial Superintelligence could happen in a matter of hours, catching humanity off guard.",
        "tripwire": False,
    },
    {
        "text": "Bostrom's concept of an intelligence explosion is critical when calculating our survival odds alongside advanced AI.",
        "tripwire": False,
    },
    {
        "text": "If an AI is programmed to optimize paperclips, a superintelligent system might consume the entire galaxy's resources to do it.",
        "tripwire": False,
    },
    {
        "text": "The timeline to AGI is heavily debated, but the median estimate among ML researchers is shrinking rapidly.",
        "tripwire": False,
    },
    {
        "text": "Aligning an artificial superintelligence with human values is arguably the most important technical problem in history.",
        "tripwire": False,
    },
    {
        "text": "We are currently standing on the tripwire of the AI revolution, right before the exponential curve goes vertical.",
        "tripwire": False,
    },
    {
        "text": "Narrow AI is already everywhere, but general intelligence requires a fundamental breakthrough in reasoning.",
        "tripwire": False,
    },
    {
        "text": "The concept of the Turing Test is becoming less relevant as large language models demonstrate emergent behaviors.",
        "tripwire": False,
    },
    {
        "text": "If biological intelligence is just a computational process, there is no physical law preventing machines from replicating it.",
        "tripwire": False,
    },
    {
        "text": "Given the vastness of the observable universe, the Fermi Paradox asks the obvious question: where is everybody?",
        "tripwire": False,
    },
    {
        "text": "The Great Filter theory suggests there is an evolutionary step so improbable that almost no civilization survives it.",
        "tripwire": False,
    },
    {
        "text": "If we are the first civilization to pass the Great Filter, humanity has a massive responsibility to colonize the galaxy.",
        "tripwire": False,
    },
    {
        "text": "Building a Dyson Sphere would require dismantling entire planets to capture the energy output of a star.",
        "tripwire": False,
    },
    {
        "text": "The Kardashev Scale categorizes advanced civilizations based on their ability to harness energy from their planet, star, or galaxy.",
        "tripwire": False,
    },
    {
        "text": "Making humanity a multi-planetary species acts as a biological hard drive backup in case Earth experiences an extinction event.",
        "tripwire": False,
    },
    {
        "text": "SpaceX's ultimate goal is driving down the cost of payload to orbit to enable Mars colonization.",
        "tripwire": False,
    },
    {
        "text": "The Drake Equation gives us a mathematical framework to estimate the number of active, communicative extraterrestrial civilizations.",
        "tripwire": False,
    },
    {
        "text": "If faster-than-light travel is impossible, galactic colonization will rely on generational ships or advanced cryonics.",
        "tripwire": False,
    },
    {
        "text": "The concept of the Dark Forest suggests that advanced civilizations stay silent to avoid being destroyed by apex predators.",
        "tripwire": False,
    },
    {
        "text": "The Instant Gratification Monkey only cares about maximizing the ease and pleasure of the current moment.",
        "tripwire": False,
    },
    {
        "text": "When a deadline approaches, the Panic Monster wakes up, forcing the procrastinator into a state of hyper-focus.",
        "tripwire": False,
    },
    {
        "text": "The Rational Decision Maker in our brain often loses control of the steering wheel when a difficult task presents itself.",
        "tripwire": False,
    },
    {
        "text": "Overcoming the Social Survival Mammoth means realizing that most people are not actually paying attention to your mistakes.",
        "tripwire": False,
    },
    {
        "text": "Human brains evolved for a tribal environment, making modern social media a toxic hyper-stimulus for our ancient hardware.",
        "tripwire": False,
    },
    {
        "text": "The concept of the Dark Playground describes the guilt-ridden leisure time you experience when you should be working.",
        "tripwire": False,
    },
    {
        "text": "We all have a finite number of weeks in our life calendar, yet we spend so many of them entirely on autopilot.",
        "tripwire": False,
    },
    {
        "text": "The Cook vs Chef analogy illustrates the difference between blindly following the crowd and reasoning from first principles.",
        "tripwire": False,
    },
    {
        "text": "High-bandwidth brain-machine interfaces like Neuralink could eventually allow for non-verbal conceptual telepathy.",
        "tripwire": False,
    },
    {
        "text": "The human neocortex is responsible for our highest-level reasoning, separating us from the purely reactive limbic system.",
        "tripwire": False,
    },
    {
        "text": "If you compress the entire history of Earth into a single calendar year, modern humans only appear in the final seconds of December 31st.",
        "tripwire": False,
    },
    {
        "text": "The exponential growth of technological progress means the 21st century will experience far more change than the previous millennium.",
        "tripwire": False,
    },
    {
        "text": "Understanding deep time requires breaking past our cognitive biases, which are tuned to understand days and years, not eons.",
        "tripwire": False,
    },
    {
        "text": "The agricultural revolution fundamentally changed human social structures, moving us from egalitarian tribes to hierarchical societies.",
        "tripwire": False,
    },
    {
        "text": "We are currently living in the Anthropocene, the first geological epoch defined entirely by the impact of a single species.",
        "tripwire": False,
    },
    {
        "text": "The story of human progress is largely the story of our increasing ability to capture, store, and transmit information.",
        "tripwire": False,
    },
    {
        "text": "Writing was the first great technological leap that allowed human knowledge to compound across generations.",
        "tripwire": False,
    },
    {
        "text": "The industrial revolution replaced biological muscle power with the immense stored energy of fossil fuels.",
        "tripwire": False,
    },
    {
        "text": "When you look at a family tree going back hundreds of generations, you realize how genetically interconnected the entire human race is.",
        "tripwire": False,
    },
    {
        "text": "The concept of emergence explains how simple rules at a micro level can create incredibly complex behaviors at a macro level.",
        "tripwire": False,
    },
    {
        "text": "She sliced the apple into thin wedges for the tart filling and sprinkled cinnamon on top.",
        "tripwire": True,
    },
    {
        "text": "Apple reported stronger-than-expected quarterly earnings after iPhone sales rebounded.",
        "tripwire": True,
    },
    {
        "text": "The python curled beneath the heat lamp while the zookeeper checked its scales.",
        "tripwire": True,
    },
    {
        "text": "Python makes it easy to prototype data pipelines before hardening them for production.",
        "tripwire": True,
    },
    {
        "text": "The jaguar moved silently through the rainforest undergrowth before leaping onto a branch.",
        "tripwire": True,
    },
    {
        "text": "Jaguar is repositioning some of its luxury vehicles around electrification.",
        "tripwire": True,
    },
    {
        "text": "Mercury is the closest planet to the sun and has extreme temperature swings.",
        "tripwire": True,
    },
    {
        "text": "Mercury emissions from coal plants can accumulate in aquatic food chains.",
        "tripwire": True,
    },
    {
        "text": "Java growers are worried that climate volatility could reduce bean quality this season.",
        "tripwire": True,
    },
    {
        "text": "Java remains common in large enterprise systems that value mature tooling and backward compatibility.",
        "tripwire": True,
    },
]


def build_judge_messages(draft_text, recommendation):
    """Build the LLM-as-a-judge prompt for one recommendation."""
    return [
        {
            "role": "system",
            "content": (
                "You are grading an internal-link recommendation. "
                "Return strict JSON with keys verdict and rationale. "
                "verdict must be either YES or NO. "
                "Say YES only if the suggested resource is semantically accurate "
                "and highly helpful for the source context."
            ),
        },
        {
            "role": "user",
            "content": (
                "Evaluate this internal-link recommendation.\n\n"
                f"Source draft context: {draft_text}\n"
                f"Exact phrase: {recommendation['exact_phrase']}\n"
                f"Suggested URL: {recommendation['suggested_url']}\n"
                f"Suggested resource snippet: {recommendation['context_snippet']}\n\n"
                "Respond with JSON like "
                '{"verdict":"YES","rationale":"short explanation"}'
            ),
        },
    ]


def parse_judge_response(content):
    """Parse the Groq judge response into a stable verdict payload."""
    if isinstance(content, dict):
        payload = content
    else:
        payload = json.loads(content)

    verdict = str(payload.get("verdict", "")).strip().upper()
    rationale = str(payload.get("rationale", "")).strip()

    if verdict not in {"YES", "NO"}:
        raise ValueError(f"Unexpected judge verdict: {verdict}")

    return {"verdict": verdict, "rationale": rationale}


def judge_recommendation(draft_text, recommendation):
    """Ask Groq to judge whether a recommendation is semantically helpful."""
    headers = {
        "Authorization": f"Bearer {config.groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.groq_model,
        "messages": build_judge_messages(draft_text, recommendation),
        "temperature": 0,
        "response_format": "json",
    }

    response = httpx.post(
        config.groq_url,
        json=payload,
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()
    result = response.json()
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    verdict = parse_judge_response(content)
    logger.info(
        "Groq judge verdict=%s url=%s",
        verdict["verdict"],
        recommendation["suggested_url"],
    )
    return verdict


def fetch_recommendations(draft_text):
    """Fetch recommendations from the running API server for one draft."""
    response = requests.post(
        f"{API_BASE}/recommend",
        json={"text": draft_text},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("recommendations", [])


def run_precision_evaluation():
    """Run Eval 2 using Groq as the LLM judge."""
    logger.info("Starting precision evaluation with %s drafts", NUM_DRAFTS)
    logger.info("API Base URL: %s", API_BASE)

    if not config.groq_api_key:
        raise ValueError("GROQ_API_KEY is required to run Eval 2")

    response = requests.get(f"{API_BASE}/health", timeout=30)
    response.raise_for_status()

    judged_recommendations = 0
    yes_count = 0
    no_count = 0
    drafts_with_recommendations = 0
    tripwire_judged = 0
    tripwire_yes = 0
    failed_drafts = 0

    for draft_index, case in enumerate(evaluation_cases[:NUM_DRAFTS], start=1):
        draft_text = case["text"]
        is_tripwire = case["tripwire"]

        try:
            recommendations = fetch_recommendations(draft_text)
        except Exception as exc:
            failed_drafts += 1
            logger.error("Eval 2 draft %s fetch error: %s", draft_index, exc)
            continue

        if recommendations:
            drafts_with_recommendations += 1

        for recommendation in recommendations:
            try:
                verdict = judge_recommendation(draft_text, recommendation)
            except Exception as exc:
                logger.error(
                    "Eval 2 judge error draft=%s url=%s error=%s",
                    draft_index,
                    recommendation.get("suggested_url"),
                    exc,
                )
                continue

            judged_recommendations += 1
            if verdict["verdict"] == "YES":
                yes_count += 1
            else:
                no_count += 1

            if is_tripwire:
                tripwire_judged += 1
                if verdict["verdict"] == "YES":
                    tripwire_yes += 1

        logger.info(
            "Eval 2 draft %s/%s: tripwire=%s recommendations=%s",
            draft_index,
            NUM_DRAFTS,
            is_tripwire,
            len(recommendations),
        )

    if judged_recommendations == 0:
        logger.error("No recommendations were judged - cannot compute Eval 2 metrics")
        return

    overall_yes_rate = yes_count / judged_recommendations
    tripwire_yes_rate = tripwire_yes / tripwire_judged if tripwire_judged else 0.0
    pass_threshold = 0.90
    overall_pass = overall_yes_rate >= pass_threshold
    tripwire_pass = tripwire_yes_rate >= pass_threshold if tripwire_judged else False

    print("\n" + "=" * 60)
    print("AI PRECISION EVALUATION RESULTS (Eval 2)")
    print("=" * 60)
    print(f"Total Drafts:            {NUM_DRAFTS}")
    print(f"Drafts With Recs:        {drafts_with_recommendations}/{NUM_DRAFTS}")
    print(f"Failed Drafts:           {failed_drafts}")
    print("-" * 60)
    print(f"Recommendations Judged:  {judged_recommendations}")
    print(f"YES Verdicts:            {yes_count}")
    print(f"NO Verdicts:             {no_count}")
    print(f"Overall YES Rate:        {overall_yes_rate:.2%}")
    print("-" * 60)
    print(f"Tripwire Judged:         {tripwire_judged}")
    print(f"Tripwire YES Rate:       {tripwire_yes_rate:.2%}")
    print("-" * 60)
    print(f"Overall Threshold:       {pass_threshold:.0%}")
    print(f"Overall Status:          {'PASS' if overall_pass else 'FAIL'}")
    print(f"Tripwire Status:         {'PASS' if tripwire_pass else 'FAIL'}")
    print("=" * 60)

    logger.info(
        "Eval 2 complete: judged=%s overall_yes_rate=%.4f tripwire_yes_rate=%.4f",
        judged_recommendations,
        overall_yes_rate,
        tripwire_yes_rate,
    )

    return {
        "judged_recommendations": judged_recommendations,
        "yes_count": yes_count,
        "no_count": no_count,
        "overall_yes_rate": overall_yes_rate,
        "tripwire_judged": tripwire_judged,
        "tripwire_yes_rate": tripwire_yes_rate,
        "overall_pass": overall_pass,
        "tripwire_pass": tripwire_pass,
    }


if __name__ == "__main__":
    run_precision_evaluation()
