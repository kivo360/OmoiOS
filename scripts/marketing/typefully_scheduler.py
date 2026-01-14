#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.25.0",
#     "python-dateutil>=2.8.0",
#     "pyyaml>=6.0",
# ]
# ///
"""
Typefully Tweet Scheduler

Reads the tweet schedule from SCHEDULE_WEEK_1_2.md and creates drafts
in Typefully with scheduled publish times for X.com.

Usage:
    # Run with uv (auto-installs dependencies)
    uv run typefully_scheduler.py --week 1          # Schedule week 1 only
    uv run typefully_scheduler.py --week 2          # Schedule week 2 only
    uv run typefully_scheduler.py --all             # Schedule both weeks
    uv run typefully_scheduler.py --dry-run --all   # Preview without creating

    # With custom start date
    uv run typefully_scheduler.py --all --start-date 2026-01-20

Environment:
    TYPEFULLY_API_KEY - Your Typefully API key (required)
"""

import os
import re
import json
import time
import httpx
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from dateutil.tz import tzlocal, gettz
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import argparse
import sys

# Import validator
from schedule_validator import (
    load_category_rules,
    validate_schedule,
    print_validation_result,
    ScheduledPost as ValidatorPost,
    SOURCE_TO_CATEGORY,
)

# ============================================================================
# Configuration
# ============================================================================

TYPEFULLY_API_BASE = "https://api.typefully.com/v2"
DEFAULT_TIMEZONE = "America/Asuncion"  # Change to your timezone

# Tweet schedule - extracted from SCHEDULE_WEEK_1_2.md
# Each entry: (day_offset, time, content, source_file, is_thread)

WEEK_1_SCHEDULE = [
    # Monday (day 0)
    (0, "09:00", """most builders quit their saas at 3-6 months in

right when:
- the messy infrastructure starts working
- growth curve actually begins

quitting right before it pays off""", "general_builder.md", False),

    (0, "12:00", """spent 3 hours yesterday watching an agent:
- try the same fix 7 times
- ignore the actual error message
- hallucinate a function that doesn't exist
- loop back to step 1

agents don't know when they're stuck

humans shouldn't have to babysit this""", "agent_problems.md", False),

    (0, "18:00", """honest question:

what's your experience with ai coding tools been like?

"game changer" or "more trouble than worth"?

genuinely curious what's working for people""", "engagement_questions.md", False),

    # Tuesday (day 1)
    (1, "09:00", """turned on "autonomous task discovery" last month

the idea: agents find optimizations and spawn new tasks

the reality:
- 10 tasks became 47
- agents "discovered" problems that weren't problems
- scope exploded
- nothing shipped

turned it off yesterday

autonomy needs constraints. learning this the hard way.""", "stories.md", False),

    (1, "12:00", """"just start coding" is advice for side projects

for production software:
- requirements get lost in slack
- design decisions are undocumented
- 3 months later nobody knows why

spec-driven isn't slow—it's insurance""", "spec_driven.md", False),

    (1, "18:00", """every cto i talk to:

"we can't hire fast enough"
"good engineers are expensive"
"onboarding takes months"
"we're behind on roadmap"

adding headcount doesn't scale linearly

what if execution could scale independently?""", "cto_pain_points.md", False),

    # Wednesday (day 2)
    (2, "09:00", """cursor helps you write code faster

but you still:
- plan the work
- coordinate the tasks
- babysit the agents
- fix stuck workflows

what if you just... didn't?""", "vision_and_product.md", False),

    (2, "12:00", """agent execution simplified:

1. receive task description
2. plan approach
3. execute steps
4. check results
5. iterate or complete

sounds simple until:
- step 3 fails silently
- step 4 hallucinates success
- step 5 loops forever

the devil is in the error handling""", "technical_education.md", False),

    (2, "18:00", """for people using cursor/copilot/antigravity:

how much time do you spend babysitting agents vs coding?

10%? 30%? 50%?

trying to understand if this is just me""", "engagement_questions.md", False),

    # Thursday (day 3)
    (3, "09:00", """cursor: ai pair programmer
antigravity: ai in your workflow
omoios: autonomous engineering execution

one helps you code
one helps you work
one works for you

different categories. different jobs.""", "competitor_callouts.md", False),

    (3, "12:00", """woke up to a $340 API bill

one agent, one night, one rabbit hole

it kept calling the LLM asking "is this right?"
the LLM kept saying "try this instead"
loop continued for 8 hours

now we have budget limits per task

expensive lessons are the ones you remember""", "failure_stories.md", False),

    (3, "18:00", """hot take: most ai coding tools are solving the wrong problem

developers don't need help WRITING code
they need help COORDINATING work

cursor makes you faster at typing
it doesn't make your team faster at shipping

different problems""", "hot_takes.md", False),

    # Friday (day 4)
    (4, "09:00", """this week's progress:

✓ phase gates working
✓ kanban real-time updates
✓ agent heartbeat monitoring
✗ guardian interventions (in testing)
✗ memory system (architecture done)

not everything ships at once
that's how software actually works""", "build_in_public.md", False),

    (4, "12:00", """ai coding without guardrails is like self-driving cars without lanes

technically possible
practically terrifying
nobody wants to be in the car""", "memes_analogies.md", False),

    (4, "18:00", """4am. still debugging.

the agent had been "working" for 6 hours
looked productive in the logs
turns out it was in a loop

same error
same fix attempt
same error
repeat 200+ times

that night i started building stuck detection

agents don't know when they're stuck
someone has to tell them""", "stories.md", False),

    # Saturday (day 5)
    (5, "10:00", """unpopular opinion:

"fully autonomous coding" is the wrong goal

you don't want ai that ships without review
you want ai that ships without BABYSITTING

review is valuable
babysitting is waste

build for the right kind of human involvement""", "hot_takes.md", False),

    (5, "15:00", """cto confession:

i spend more time in meetings about the roadmap
than my team spends actually building the roadmap

something is wrong with this model""", "customer_avatars.md", False),

    # Sunday (day 6) - Thread
    (6, "11:00", [
        """🧵 Why AI coding agents fail (and what we can do about it)

A thread on the real problems with autonomous coding, and the architecture decisions that actually matter.""",
        """1/ The Stuck Problem

Agents don't know when they're stuck.

They'll try the same fix 10 times in a row, burn through tokens, and ask YOU what's wrong.

This isn't an LLM problem. It's an architecture problem.""",
        """2/ The Drift Problem

Give an agent a simple task.
Watch it "improve" unrelated code.
See it add features nobody asked for.
Find it refactoring your state management.

Agents optimize for "helpful."
Not for "focused." """,
        """3/ The Context Cliff

Context windows aren't infinite.

At some point, your original requirements fall off the edge.

The agent forgets what "done" looks like.

Long sessions = inevitable drift.""",
        """4/ The Hallucination Gap

Agent says "fixed!"
Code looks reasonable.
Tests pass.

Ship to production: broken.

The fix called a function that doesn't exist.
The tests were mocked.
Confidence ≠ correctness.""",
        """5/ What Actually Works

- Short, focused tasks (not marathon sessions)
- Explicit specs (not vibes)
- Stuck detection (monitor for loops)
- Phase gates (human checkpoints)
- Mutual verification (agents check each other)

Architecture beats bigger models.""",
        """6/ The Takeaway

AI coding tools overpromise.

The solution isn't "better AI."
It's better architecture AROUND the AI.

Constraints enable autonomy.
Structure prevents chaos.

/end thread"""
    ], "threads.md", True),
]

WEEK_2_SCHEDULE = [
    # Monday (day 7)
    (7, "09:00", """the gap between 'i have an idea' and 'i shipped something' is like 2 weeks max

but most stretch it to months with overthinking

just build the mvp—ideas die in your head""", "general_builder.md", False),

    (7, "12:00", """the fundamental problem with ai coding:

agents optimize for "generate code"
not for "solve the problem"

they'll write 500 lines that compile perfectly
and miss the actual requirement entirely

this is an architecture problem, not a model problem""", "agent_problems.md", False),

    (7, "18:00", """if ai could code autonomously:

how much oversight would you want?

a) review every line
b) review at checkpoints
c) just review the PR
d) full send, trust the ai

curious where people land on this""", "engagement_questions.md", False),

    # Tuesday (day 8)
    (8, "09:00", """watched an ai coding demo last week

"build me a todo app"
*30 seconds later*
"here's your app!"

what they didn't show:
- the 6 previous attempts
- the manual fixes
- the broken tests
- it only works for todo apps

i've been building ai coding tools for 8 months

demos aren't reality. production is.""", "stories.md", False),

    (8, "12:00", """watched a team ship a feature last month

6 weeks of work
merged to main
product says "that's not what i meant"

no requirements doc
no design review
just vibes

spec-driven development exists because this keeps happening""", "spec_driven.md", False),

    (8, "18:00", """engineering teams at 50+ people:

- 4 hours/week in standups
- 3 hours/week in planning
- 2 hours/week in retros
- 5 hours/week in status updates

that's 14 hours/week NOT building

coordination is the hidden tax on engineering""", "cto_pain_points.md", False),

    # Wednesday (day 9)
    (9, "09:00", """most ai coding tools: "build me X" → agent starts coding immediately

the problem:
- no requirements
- no design
- no plan

garbage in, garbage out

spec-driven > vibe-driven""", "vision_and_product.md", False),

    (9, "12:00", """spec-driven api development:

requirement: "POST /api/tasks creates task, returns 201, validates input"

agent gets:
- exact endpoint path
- expected status code
- input validation rules
- response schema

vs vibe: "make an endpoint for tasks"

one is testable
one is vibes""", "use_cases.md", False),

    (9, "18:00", """why agents hallucinate:

llm sees: "file not found error"
llm thinks: "i'll create the file"
llm doesn't check: "does this file SHOULD exist?"

agents execute without questioning

verification is the missing layer""", "technical_education.md", False),

    # Thursday (day 10)
    (10, "09:00", """every time you start a new cursor chat:

- agent forgets your codebase patterns
- agent forgets the bug it fixed yesterday
- agent forgets your team's conventions

what if agents remembered?

what if they got smarter over time?""", "competitor_callouts.md", False),

    (10, "12:00", """let an agent run unsupervised for 2 hours once

came back to:
- 14 commits
- 3 "refactoring improvements" nobody asked for
- a broken build
- tests disabled "temporarily"

that's when i understood phase gates

autonomy without checkpoints = chaos""", "failure_stories.md", False),

    (10, "18:00", """"ai will replace developers" is wrong

ai will replace:
- boilerplate writing
- pattern implementation
- test scaffolding
- documentation

ai won't replace:
- architecture decisions
- requirement gathering
- debugging production
- understanding users

different job. not the same job.""", "hot_takes.md", False),

    # Friday (day 11)
    (11, "09:00", """bugs we fixed this week:

- agents not detecting stuck loops
- tasks spawning without context
- websocket disconnects on long runs
- memory leaks in agent workers

the boring infrastructure nobody sees

but it's what makes the system actually work""", "build_in_public.md", False),

    (11, "12:00", """ai agents are like brilliant interns:

- enthusiastic
- fast
- technically capable
- zero judgment
- need constant supervision
- will confidently do the wrong thing

except the intern learns and stays""", "memes_analogies.md", False),

    (11, "18:00", """when ai agents get stuck in your workflow:

how do you usually find out?
how long does it take?

wondering if this is a universal pain point""", "engagement_questions.md", False),

    # Saturday (day 12)
    (12, "10:00", """the problem with ai coding demos:

they show: "look it built a todo app!"

they hide:
- 47 prompts to get there
- 3 sessions that failed
- manual fixes they edited out
- it only works for simple cases

demos aren't reality

production is reality""", "hot_takes.md", False),

    (12, "15:00", """my morning routine:

7am: arrive before team
7:15: open PR queue
7:16: 14 PRs waiting
7:17: sigh
10am: reviewed 6 PRs
10:01: 4 new PRs arrived

the pile never shrinks""", "customer_avatars.md", False),

    # Sunday (day 13) - Thread
    (13, "11:00", [
        """🧵 Why spec-driven development beats "vibe coding" for production software

A thread on why structure matters more than speed when AI is doing the work.""",
        """1/ The Vibe Coding Problem

"Build me a payment system"
→ Agent starts coding immediately
→ No requirements
→ No design
→ No acceptance criteria

4 hours later: wrong thing, built confidently.""",
        """2/ What Specs Provide

Requirements → "here's what done looks like"
Design → "here's how components fit together"
Tasks → "here's discrete work units"

Without these, agents have no reference point.
They're guessing what you want.""",
        """3/ The Debugging Problem

Vibe-coded feature doesn't work.
How do you debug it?

Compare to... what?

Spec-coded feature doesn't work.
Compare to requirements.
Find the gap.
Fix the gap.

Specs are debugging documentation.""",
        """4/ The AI Multiplier

Specs matter more with AI because:

- AI executes faster (wrong direction costs more)
- AI doesn't ask clarifying questions
- AI optimizes for completion, not correctness

More speed requires more guardrails.""",
        """5/ The Process

1. Requirements (what must it do?)
2. Design (how will it work?)
3. Tasks (what are the work units?)
4. Execution (agent does the work)
5. Verification (does it match the spec?)

Slow down to speed up.

/end thread"""
    ], "threads.md", True),
]

WEEK_3_SCHEDULE = [
    # Monday (day 14)
    (14, "09:00", """building a product:
90% backend plumbing nobody sees
10% ui everyone judges you on

focus on the invisible work first—it holds everything together""", "general_builder.md", False),

    (14, "12:00", """cursor agent yesterday:

installed a package
broke the build
didn't notice
kept coding
broke it more
asked me what's wrong

no feedback loop = no self-correction

agents need to verify their own work""", "agent_problems.md", False),

    (14, "18:00", """ctos and engineering managers:

what's your biggest bottleneck right now?

- hiring
- coordination
- code review
- planning
- all of the above

genuinely want to know""", "engagement_questions.md", False),

    # Tuesday (day 15)
    (15, "09:00", """call with a CTO last week:

him: "we need to ship faster"
me: "how many engineers?"
him: "47"
me: "how many in meetings right now?"
him: "...probably 30"
me: "that's your problem"

coordination tax is invisible until you count it""", "stories.md", False),

    (15, "12:00", """the spec isn't for the AI

it's for YOU

when the AI builds something wrong, you need:
- requirements to compare against
- design decisions documented
- clear acceptance criteria

vibes can't be debugged""", "spec_driven.md", False),

    (15, "18:00", """every product roadmap i've seen:

q1 plan: 20 features
q1 shipped: 8 features
q2 plan: 20 features + 12 carryover
q2 shipped: 6 features

the backlog grows faster than you ship

this isn't a planning problem—it's a capacity problem""", "cto_pain_points.md", False),

    # Wednesday (day 16)
    (16, "09:00", """what if:
- you describe a feature
- system generates requirements
- you approve the design
- agents execute in parallel
- you review the PR

not "ai writes code for you"
but "ai runs your engineering process"

that's the difference between a tool and a platform""", "vision_and_product.md", False),

    (16, "12:00", """spec-driven migrations:

1. design specifies exact schema
2. task: "create migration for users table with fields X, Y, Z"
3. agent implements migration
4. validation: compare output to design spec

vs vibe: "add users to the database"

which one would you trust in production?""", "use_cases.md", False),

    (16, "18:00", """context windows explained:

agent starts: full context
agent works: context fills up
agent continues: old context drops

by the end of a session:
- forgot the original goal
- lost track of constraints
- missing critical context

this is why sessions break down

architecture > bigger context windows""", "technical_education.md", False),

    # Thursday (day 17)
    (17, "09:00", """watched a cursor agent loop on the same error for 20 minutes yesterday

it didn't know it was stuck
i had to intervene

imagine if agents could detect drift and correct themselves

that's not fantasy—it's architecture""", "competitor_callouts.md", False),

    (17, "12:00", """agent confidently told me it fixed the bug

checked the code: looked reasonable
ran the tests: all passed
shipped to staging: broken

the "fix" was calling a function that doesn't exist
the tests were mocked
the agent hallucinated success

verification isn't optional anymore""", "failure_stories.md", False),

    (17, "18:00", """agent frameworks are infrastructure, not products

users don't want "agents"
users want "shipped features"

the framework is invisible
the output is what matters

stop selling agents
start selling outcomes""", "hot_takes.md", False),

    # Friday (day 18)
    (18, "09:00", """turned off discovery branching yesterday

why:
- agents were spawning irrelevant tasks
- "optimizations" nobody asked for
- scope kept expanding
- 10 tasks became 47

autonomy without constraints = chaos

learning this the hard way so you don't have to""", "build_in_public.md", False),

    (18, "12:00", """ai agents without specs are like GPS without a destination

they'll move confidently
in some direction
very efficiently
to somewhere you didn't want to go""", "memes_analogies.md", False),

    # Saturday (day 19)
    (19, "10:00", """unpopular opinion: bigger context windows won't save ai coding

100k tokens means:
- 100k tokens of potential drift
- 100k tokens of accumulated errors
- 100k tokens of hallucination opportunity

architecture > context size

structure beats brute force""", "hot_takes.md", False),

    (19, "15:00", """every monday:

- 23 tickets in backlog
- 4 engineers in meetings
- 2 PRs waiting for review since friday
- 1 critical bug from the weekend
- 0 clarity on what we'll actually ship

and they wonder why i look tired""", "customer_avatars.md", False),

    # Sunday (day 20)
    (20, "10:00", """hot take: "vibe coding" is actively harmful for production

it's fun for:
- side projects
- learning
- prototypes

it's dangerous for:
- enterprise software
- regulated industries
- anything with users

discipline isn't the enemy of speed""", "hot_takes.md", False),

    (20, "15:00", """🧵 the spec-driven development manifesto

why structured specs beat "vibe coding" for production:

(thread)""", "threads.md", False),
]

WEEK_4_SCHEDULE = [
    # Monday (day 21)
    (21, "09:00", """founders chase 'viral' features for hype

instead:
- nail the core problem
- make it stupid simple

users come for value, not fireworks""", "general_builder.md", False),

    (21, "12:00", """gave an agent a simple task:
"add input validation to the form"

20 minutes later it was:
- refactoring the state management
- "improving" the component structure
- adding features i didn't ask for

agents drift. constantly.

without monitoring, they'll wander forever""", "agent_problems.md", False),

    (21, "18:00", """when you use ai coding tools:

do you write specs first?
or just describe what you want?

no judgment - just curious about workflows""", "engagement_questions.md", False),

    # Tuesday (day 22)
    (22, "09:00", """senior engineer told me last week:

"i spend more time reviewing AI code than writing my own"

he wasn't complaining
he was exhausted

ai coding tools shifted the bottleneck
from writing to reviewing

the work didn't disappear
it just moved""", "stories.md", False),

    (22, "12:00", """most ai coding flows:
user: "build X"
ai: *starts coding immediately*

what's missing:
- edge cases
- error handling
- integration points
- acceptance criteria

our flow forces requirements BEFORE code

"slow down to speed up" isn't just a saying""", "spec_driven.md", False),

    (22, "18:00", """same feature request
3 different engineers
3 different implementations:
- different patterns
- different error handling
- different test coverage

consistency requires coordination

coordination requires time

time is the bottleneck""", "cto_pain_points.md", False),

    # Wednesday (day 23)
    (23, "09:00", """"fully autonomous coding" sounds great until:

- agent merges broken code to main
- agent refactors something it shouldn't
- agent burns $50 in tokens on a rabbit hole

autonomy without oversight = chaos

autonomy WITH phase gates = shipping""", "vision_and_product.md", False),

    (23, "12:00", """phase gate in action:

phase 1: requirements doc approved ✓
phase 2: design doc approved ✓
phase 3: tasks breakdown approved ✓
phase 4: agents execute autonomously
phase 5: PR ready for review

human involved at decision points
ai handles execution between

control + speed""", "use_cases.md", False),

    (23, "18:00", """multi-agent coordination patterns:

1. workspace isolation (git worktrees)
2. file locking (prevent conflicts)
3. dependency ordering (don't start what's blocked)
4. result aggregation (combine outputs)
5. failure handling (don't cascade crashes)

"run multiple agents" is easy
"run multiple agents correctly" is engineering""", "technical_education.md", False),

    # Thursday (day 24)
    (24, "09:00", """google antigravity shows you what agents did

artifacts are nice

but:
- agents still get stuck
- you still babysit execution
- no self-healing
- no spec-driven workflow

visibility isn't the same as reliability""", "competitor_callouts.md", False),

    (24, "12:00", """task: "add input validation to the signup form"

what i got back:
- form completely redesigned
- state management refactored
- 4 new components created
- validation logic in 3 different places
- original form: still no validation

drift is the silent killer""", "failure_stories.md", False),

    (24, "18:00", """hot take: ai coding makes senior engineers MORE valuable, not less

ai can:
- write code quickly
- implement patterns

ai can't:
- make architecture decisions
- debug subtle production issues
- understand business context
- mentor juniors

seniors review, guide, decide
ai executes""", "hot_takes.md", False),

    # Friday (day 25)
    (25, "09:00", """ai coding tools overpromise

"build apps with just english!"
"10x developer productivity!"
"ship features in minutes!"

reality:
- agents get stuck constantly
- context limits hurt
- hallucinations happen
- debugging AI is harder than writing code

we're building for reality, not demos""", "build_in_public.md", False),

    (25, "12:00", """giving an ai agent unlimited autonomy is like:

hiring a chef
giving them your kitchen
leaving for a week
hoping the house doesn't burn down

you might come back to a gourmet meal
or ash""", "memes_analogies.md", False),

    # Saturday (day 26)
    (26, "10:00", """hot take: free ai coding tools are traps

google antigravity is free because:
- you're the product
- data trains their models
- ecosystem lock-in is the goal

"free" has a price
you just pay differently""", "hot_takes.md", False),

    (26, "15:00", """tried ai coding tools last quarter

the pitch: "10x productivity!"

the reality:
- agents got stuck constantly
- spent more time babysitting than coding
- code quality was inconsistent
- rolled back to manual work

i want to believe
but i've been burned""", "customer_avatars.md", False),

    # Sunday (day 27)
    (27, "10:00", """controversial take: ai won't 10x engineering teams

it might:
- 1.5x individual productivity
- shift bottleneck from coding to review
- create new failure modes

the hype says 10x
the reality says "it's complicated"

manage expectations or get disappointed""", "hot_takes.md", False),

    (27, "15:00", """🧵 why multi-agent coding is harder than it looks

running 8 agents in parallel sounds cool—until they step on each other

(thread)""", "threads.md", False),
]


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ScheduledPost:
    """Represents a single scheduled post"""
    day_offset: int
    time: str
    content: str | list[str]
    source: str
    is_thread: bool
    scheduled_datetime: Optional[datetime] = None

    def get_title(self) -> str:
        """Generate a title for the draft"""
        if self.is_thread:
            return f"Thread: {self.content[0][:50]}..."
        return f"{self.content[:50]}..."


@dataclass
class TypefullyClient:
    """Client for Typefully API v2"""
    api_key: str
    base_url: str = TYPEFULLY_API_BASE
    timezone: str = DEFAULT_TIMEZONE

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_me(self) -> dict:
        """Get authenticated user info"""
        print(f"[DEBUG] get_me: calling {self.base_url}/me", flush=True)
        with httpx.Client(timeout=30.0) as client:
            print("[DEBUG] get_me: client created, making request...", flush=True)
            resp = client.get(f"{self.base_url}/me", headers=self._headers())
            print(f"[DEBUG] get_me: got response {resp.status_code}", flush=True)
            resp.raise_for_status()
            return resp.json()

    def get_social_sets(self) -> list[dict]:
        """Get all connected social accounts"""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.base_url}/social-sets", headers=self._headers())
            resp.raise_for_status()
            return resp.json().get("results", [])

    def create_draft(
        self,
        social_set_id: str,
        posts: list[str],
        publish_at: Optional[str] = None,
        draft_title: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> tuple[dict, dict]:
        """
        Create a new draft for X (Twitter)

        Args:
            social_set_id: The social set ID to post to
            posts: List of tweet texts (multiple = thread)
            publish_at: ISO datetime, "now", "next-free-slot", or None for draft
            draft_title: Optional title for the draft
            tags: Optional list of tag slugs

        Returns:
            Tuple of (response_json, rate_limit_info)
        """
        # Build X posts array
        x_posts = [{"text": text, "media_ids": []} for text in posts]

        payload = {
            "platforms": {
                "x": {
                    "enabled": True,
                    "posts": x_posts,
                    "settings": {}
                }
            }
        }

        if publish_at:
            payload["publish_at"] = publish_at

        if draft_title:
            payload["draft_title"] = draft_title

        if tags:
            payload["tags"] = tags

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.base_url}/social-sets/{social_set_id}/drafts",
                headers=self._headers(),
                json=payload
            )

            # Extract rate limit headers
            rate_limit_info = {
                "user_limit": resp.headers.get("X-RateLimit-User-Limit"),
                "user_remaining": resp.headers.get("X-RateLimit-User-Remaining"),
                "user_reset": resp.headers.get("X-RateLimit-User-Reset"),
                "socialset_limit": resp.headers.get("X-RateLimit-SocialSet-Limit"),
                "socialset_remaining": resp.headers.get("X-RateLimit-SocialSet-Remaining"),
                "socialset_reset": resp.headers.get("X-RateLimit-SocialSet-Reset"),
                "socialset_resource": resp.headers.get("X-RateLimit-SocialSet-Resource"),
            }

            resp.raise_for_status()
            return resp.json(), rate_limit_info

    def get_drafts(self, social_set_id: str, limit: int = 50) -> list[dict]:
        """Get existing drafts"""
        print(f"[DEBUG] get_drafts: fetching from social_set_id={social_set_id}", flush=True)
        with httpx.Client(timeout=30.0) as client:
            print("[DEBUG] get_drafts: client created, making request...", flush=True)
            resp = client.get(
                f"{self.base_url}/social-sets/{social_set_id}/drafts",
                headers=self._headers(),
                params={"limit": limit}
            )
            print(f"[DEBUG] get_drafts: got response {resp.status_code}", flush=True)
            resp.raise_for_status()
            return resp.json().get("results", [])


# ============================================================================
# Scheduler Logic
# ============================================================================

def calculate_schedule_times(
    schedule: list[tuple],
    start_date: datetime,
    timezone_str: str
) -> list[ScheduledPost]:
    """
    Calculate actual datetime for each scheduled post

    Args:
        schedule: List of (day_offset, time, content, source, is_thread)
        start_date: The Monday to start from
        timezone_str: Timezone string (e.g., "America/New_York")
    """
    tz = gettz(timezone_str)
    posts = []

    for day_offset, time_str, content, source, is_thread in schedule:
        # Parse time
        hour, minute = map(int, time_str.split(":"))

        # Calculate datetime
        post_date = start_date + timedelta(days=day_offset)
        post_datetime = post_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Ensure timezone
        if post_datetime.tzinfo is None:
            post_datetime = post_datetime.replace(tzinfo=tz)

        posts.append(ScheduledPost(
            day_offset=day_offset,
            time=time_str,
            content=content,
            source=source,
            is_thread=is_thread,
            scheduled_datetime=post_datetime
        ))

    return posts


def format_datetime_for_api(dt: datetime) -> str:
    """Format datetime for Typefully API (ISO 8601 with timezone)"""
    return dt.isoformat()


def get_day_name(day_offset: int) -> str:
    """Get day name from offset"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[day_offset % 7]


# ============================================================================
# Main Script
# ============================================================================

def main():
    print("[DEBUG] Starting main()", flush=True)
    parser = argparse.ArgumentParser(
        description="Schedule tweets to Typefully from the OmoiOS swipe file"
    )
    parser.add_argument(
        "--week",
        type=int,
        choices=[1, 2, 3, 4],
        help="Schedule only a specific week (1, 2, 3, or 4)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Schedule all 4 weeks"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview schedule without creating drafts"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (Monday) in YYYY-MM-DD format. Defaults to next Monday."
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default=DEFAULT_TIMEZONE,
        help=f"Timezone for scheduling (default: {DEFAULT_TIMEZONE})"
    )
    parser.add_argument(
        "--list-accounts",
        action="store_true",
        help="List connected social accounts and exit"
    )
    parser.add_argument(
        "--social-set-id",
        type=str,
        help="Specific social set ID to use (run --list-accounts to find)"
    )
    parser.add_argument(
        "--reschedule-past",
        action="store_true",
        help="For posts scheduled in the past, use 'next-free-slot' instead of failing"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate schedule against category rules without posting"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any validation warnings (not just errors)"
    )
    parser.add_argument(
        "--draft-only",
        action="store_true",
        help="Create as drafts only (no scheduled publish time) - useful to bypass rate limits"
    )

    args = parser.parse_args()
    print(f"[DEBUG] Parsed args: week={args.week}, all={args.all}, dry_run={args.dry_run}, draft_only={args.draft_only}", flush=True)

    # Get API key
    api_key = os.environ.get("TYPEFULLY_API_KEY")
    if not api_key:
        print("ERROR: TYPEFULLY_API_KEY environment variable not set")
        print("\nTo get your API key:")
        print("1. Go to https://typefully.com/settings")
        print("2. Navigate to API section")
        print("3. Generate a new API key")
        print("\nThen run:")
        print('  export TYPEFULLY_API_KEY="your_key_here"')
        sys.exit(1)

    # Initialize client
    print("[DEBUG] Initializing client...", flush=True)
    client = TypefullyClient(api_key=api_key, timezone=args.timezone)
    print("[DEBUG] Client initialized", flush=True)

    # Test connection and get user
    print("[DEBUG] Testing connection...", flush=True)
    try:
        user = client.get_me()
        print(f"✓ Connected as: {user.get('name', user.get('email', 'Unknown'))}", flush=True)
        print("[DEBUG] Connection test done", flush=True)
    except httpx.HTTPStatusError as e:
        print(f"ERROR: Failed to authenticate: {e}", flush=True)
        sys.exit(1)

    # Get social sets
    print("[DEBUG] Getting social sets...", flush=True)
    social_sets = client.get_social_sets()
    print(f"[DEBUG] Got {len(social_sets)} social sets", flush=True)

    if not social_sets:
        print("ERROR: No connected social accounts found")
        print("Connect your X account at https://typefully.com/settings")
        sys.exit(1)

    print("[DEBUG] Checking list_accounts mode...", flush=True)

    # List accounts mode
    if args.list_accounts:
        print("\n📱 Connected Social Accounts:")
        print("-" * 60)
        for ss in social_sets:
            print(f"  ID: {ss['id']}")
            print(f"  Name: {ss.get('name', 'Unknown')}")
            if ss.get('username'):
                print(f"  X Handle: @{ss.get('username')}")
            print()
        sys.exit(0)

    # Determine which social set to use
    print("[DEBUG] Determining social set...", flush=True)
    social_set_id = args.social_set_id
    if not social_set_id:
        # Use first available social set (Typefully social sets are typically X accounts)
        if social_sets:
            ss = social_sets[0]
            social_set_id = str(ss["id"])
            x_handle = ss.get('username', 'unknown')
            print(f"✓ Using X account: @{x_handle}", flush=True)
    print(f"[DEBUG] social_set_id = {social_set_id}", flush=True)

    if not social_set_id:
        print("ERROR: No social sets found")
        sys.exit(1)

    # Validate week selection
    print("[DEBUG] Validating week selection...", flush=True)
    if not args.week and not args.all:
        print("ERROR: Specify --week 1, --week 2, --week 3, --week 4, or --all")
        sys.exit(1)

    print("[DEBUG] Determining start date...", flush=True)
    # Determine start date
    if args.start_date:
        start_date = date_parser.parse(args.start_date)
        tz = gettz(args.timezone)
        start_date = start_date.replace(tzinfo=tz)
    else:
        # Default to next Monday
        today = datetime.now(gettz(args.timezone))
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # Next Monday, not today
        start_date = today + timedelta(days=days_until_monday)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    print(f"✓ Schedule starts: {start_date.strftime('%A, %B %d, %Y')}", flush=True)
    print(f"✓ Timezone: {args.timezone}", flush=True)

    print("[DEBUG] Building schedule...", flush=True)
    # Build schedule
    schedule = []
    if args.week == 1 or args.all:
        schedule.extend(WEEK_1_SCHEDULE)
    if args.week == 2 or args.all:
        schedule.extend(WEEK_2_SCHEDULE)
    if args.week == 3 or args.all:
        schedule.extend(WEEK_3_SCHEDULE)
    if args.week == 4 or args.all:
        schedule.extend(WEEK_4_SCHEDULE)

    print(f"[DEBUG] Schedule built with {len(schedule)} posts", flush=True)

    # Calculate times
    print("[DEBUG] Calculating schedule times...", flush=True)
    posts = calculate_schedule_times(schedule, start_date, args.timezone)
    print(f"[DEBUG] Calculated times for {len(posts)} posts", flush=True)

    # Validate schedule if requested
    if args.validate or not args.dry_run:
        print("\n🔍 Validating schedule against category rules...", flush=True)

        # Load rules from swipe file frontmatter
        print("[DEBUG] Finding swipe dir...", flush=True)
        script_dir = Path(__file__).parent
        swipe_dir = script_dir.parent.parent / "docs" / "marketing" / "swipe_file"
        print(f"[DEBUG] swipe_dir = {swipe_dir}", flush=True)
        print("[DEBUG] Loading category rules...", flush=True)
        rules = load_category_rules(swipe_dir)
        print(f"  Loaded rules for {len(rules)} categories", flush=True)

        print("[DEBUG] Converting posts to validator format...", flush=True)
        # Convert posts to validator format
        validator_posts = [
            ValidatorPost(
                index=i,
                content=p.content[0] if p.is_thread else p.content,
                source=p.source,
                scheduled_datetime=p.scheduled_datetime,
                is_thread=p.is_thread,
            )
            for i, p in enumerate(posts)
        ]
        print(f"[DEBUG] Created {len(validator_posts)} validator posts", flush=True)

        # Run validation
        print("[DEBUG] Running validate_schedule...", flush=True)
        validation_result = validate_schedule(validator_posts, rules, start_date)
        print("[DEBUG] Validation complete, printing results...", flush=True)
        print_validation_result(validation_result)
        print("[DEBUG] Validation results printed", flush=True)

        # Handle validation-only mode
        if args.validate:
            sys.exit(0 if validation_result.is_valid else 1)

        # In strict mode, fail on warnings too
        if args.strict and validation_result.warnings:
            print("\n❌ Strict mode: failing due to warnings")
            sys.exit(1)

        # In normal mode, fail only on errors
        if not validation_result.is_valid:
            print("\n❌ Schedule has errors. Use --dry-run to preview anyway, or fix errors first.")
            sys.exit(1)

    # Fetch existing drafts to prevent duplicates
    print("[DEBUG] About to fetch existing drafts...", flush=True)
    existing_drafts = []
    # Always fetch drafts to show accurate duplicate detection in dry-run
    print("\n🔍 Checking for existing drafts...", flush=True)
    try:
        existing_drafts = client.get_drafts(social_set_id, limit=50)  # API max is 50
        print(f"  Found {len(existing_drafts)} existing drafts", flush=True)
    except Exception as e:
        print(f"  Could not fetch existing drafts ({e}), proceeding anyway", flush=True)
    print("[DEBUG] Done fetching drafts", flush=True)

    # Build a set of existing content signatures for duplicate detection
    print("[DEBUG] Building signatures set...", flush=True)
    existing_signatures = set()
    for draft in existing_drafts:
        # Use preview field for content matching (first ~200 chars of first tweet)
        preview = draft.get("preview", "")
        if preview:
            signature = preview[:100].strip().lower()
            existing_signatures.add(signature)
    print(f"[DEBUG] Built {len(existing_signatures)} signatures", flush=True)

    print(f"\n📅 Scheduling {len(posts)} posts...", flush=True)
    print("=" * 60, flush=True)

    # Dry run or execute
    created_count = 0
    skipped_count = 0
    thread_count = 0

    print("[DEBUG] Starting loop over posts...", flush=True)
    for post_idx, post in enumerate(posts):
        print(f"[DEBUG] Processing post {post_idx + 1}/{len(posts)}", flush=True)
        day_name = get_day_name(post.day_offset)
        time_str = post.scheduled_datetime.strftime("%I:%M %p")
        date_str = post.scheduled_datetime.strftime("%b %d")

        if post.is_thread:
            preview = f"🧵 Thread ({len(post.content)} tweets)"
            thread_count += 1
            # For threads, check first tweet
            content_signature = post.content[0][:100].strip().lower()
        else:
            preview = post.content[:60].replace("\n", " ") + "..."
            content_signature = post.content[:100].strip().lower()

        print(f"\n{day_name}, {date_str} @ {time_str}")
        print(f"  {preview}")
        print(f"  Source: {post.source}")

        # Check for duplicate
        if content_signature in existing_signatures:
            print(f"  ⏭️  SKIPPED: Similar content already exists")
            skipped_count += 1
            continue

        if not args.dry_run:
            # Prepare content
            if post.is_thread:
                content_list = post.content
            else:
                content_list = [post.content]

            # Determine publish_at
            if args.draft_only:
                # Create as draft only - no scheduled time
                publish_at = None
                print(f"  📝 Creating as draft (no schedule)")
            else:
                # Check if scheduled time is in the past
                now = datetime.now(gettz(args.timezone))
                if post.scheduled_datetime < now:
                    if args.reschedule_past:
                        # Use next-free-slot for past dates
                        publish_at = "next-free-slot"
                        print(f"  📅 Rescheduling to next free slot (original time was in past)")
                    else:
                        # Will fail with API error
                        publish_at = format_datetime_for_api(post.scheduled_datetime)
                else:
                    publish_at = format_datetime_for_api(post.scheduled_datetime)

            # Retry logic for rate limiting - Typefully has aggressive limits
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # Create draft with schedule
                    result, rate_info = client.create_draft(
                        social_set_id=social_set_id,
                        posts=content_list,
                        publish_at=publish_at,
                        draft_title=f"[Auto] {day_name} {time_str}"
                    )

                    print(f"  ✓ Created draft: {result.get('id', 'unknown')}", flush=True)

                    # Log rate limit info
                    remaining = rate_info.get("socialset_remaining") or rate_info.get("user_remaining")
                    limit = rate_info.get("socialset_limit") or rate_info.get("user_limit")
                    if remaining and limit:
                        print(f"  [RATE] {remaining}/{limit} requests remaining", flush=True)

                    created_count += 1

                    # Add to existing signatures to prevent duplicates within this run
                    existing_signatures.add(content_signature)

                    # Rate limiting: wait based on remaining requests
                    if remaining and int(remaining) <= 2:
                        # Very close to limit, wait longer
                        reset_ts = rate_info.get("socialset_reset") or rate_info.get("user_reset")
                        if reset_ts:
                            wait_until = int(reset_ts)
                            now_ts = int(time.time())
                            wait_time = max(wait_until - now_ts + 5, 60)  # Wait until reset + 5s, min 60s
                            print(f"  [RATE] Near limit, waiting {wait_time}s until reset...", flush=True)
                            time.sleep(wait_time)
                        else:
                            print(f"  [RATE] Near limit, waiting 60s...", flush=True)
                            time.sleep(60)
                    else:
                        # Normal delay between requests
                        print(f"  [DEBUG] Waiting 3s before next request...", flush=True)
                        time.sleep(3)
                    break  # Success, exit retry loop

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        # Extract rate limit reset time from 429 response headers
                        reset_ts = e.response.headers.get("X-RateLimit-SocialSet-Reset") or e.response.headers.get("X-RateLimit-User-Reset")
                        if reset_ts:
                            now_ts = int(time.time())
                            wait_time = max(int(reset_ts) - now_ts + 5, 30)  # Wait until reset + 5s, min 30s
                            print(f"  ⏳ Rate limited, reset in {wait_time}s (attempt {attempt + 1}/{max_retries})", flush=True)
                        else:
                            # Fallback: exponential backoff
                            wait_time = (attempt + 1) * 60  # 60s, 120s, 180s, 240s, 300s
                            print(f"  ⏳ Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})", flush=True)

                        time.sleep(wait_time)
                        if attempt == max_retries - 1:
                            print(f"  ✗ Failed after {max_retries} retries: rate limited", flush=True)
                            print(f"  💡 Tip: Try running again later or use --dry-run to preview", flush=True)
                    else:
                        print(f"  ✗ Failed: {e.response.status_code} - {e.response.text[:100]}", flush=True)
                        break  # Non-rate-limit error, don't retry
                except Exception as e:
                    print(f"  ✗ Error: {e}", flush=True)
                    break  # Unexpected error, don't retry

    # Summary
    print("\n" + "=" * 60)
    if args.dry_run:
        print(f"DRY RUN COMPLETE")
        print(f"  Would create: {len(posts)} drafts ({thread_count} threads)")
    else:
        print(f"SCHEDULING COMPLETE")
        print(f"  Created: {created_count} drafts")
        if skipped_count > 0:
            print(f"  Skipped: {skipped_count} (already exist)")
        print(f"  Threads: {thread_count}")
        print(f"  Total processed: {len(posts)}")

    print(f"\nView your drafts at: https://typefully.com/drafts")


if __name__ == "__main__":
    main()
