const { Document, Packer, Paragraph, TextRun, HeadingLevel, PageBreak, BorderStyle, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType } = require('docx');
const fs = require('fs');

// Series Framework
const seriesTitle = "The Mental Game: Building in Public";
const seriesTagline = "What nobody tells you about the unglamorous reality of building a startup";

// Post 1: The Imposter Within
const post1 = {
  title: "Post 1: The Voice That Says You're Not Ready",
  theme: "Imposter Syndrome / Not Ready Enough",
  rawVersion: `I'm about to launch something and there's a voice in my head that won't shut up.

"You're not ready."
"This isn't good enough."
"People are going to see right through you."

Here's the thing nobody talks about: that voice doesn't go away when you've "made it." It's there at $0. It'll be there at $10k MRR. It's the tax you pay for giving a shit.

The difference between people who ship and people who don't isn't the absence of that voice. It's shipping anyway.

I'm launching in 3 weeks. The voice is screaming. I'm doing it anyway.

What's the voice telling you right now?`,

  polishedVersion: `I'm preparing to launch a product, and I'd be lying if I said the self-doubt wasn't loud.

"You're not ready yet."
"It needs more polish."
"People will see the gaps."

Here's what I've realized: that internal resistance doesn't disappear with more preparation. It's present whether you're at zero revenue or substantial traction. It's the cost of caring about what you're building.

The distinction between builders who ship and those who don't isn't confidence—it's action despite uncertainty.

I'm launching in three weeks. The doubt is present. I'm moving forward regardless.

What internal resistance are you navigating right now?`
};

// Post 2: The Hate Spiral
const post2 = {
  title: "Post 2: People Are Going to Hate Me",
  theme: "Fear of Judgment / Comparison to Highlight Reels",
  rawVersion: `"People are going to hate me."

I've said this to myself probably 50 times this week. Not exaggerating.

I look at other launches. Beautiful landing pages. Polished demos. Founders who seem to have their shit together.

Then I look at my thing. It's not as pretty. The demo has rough edges. My voiceover sounds like I recorded it at 2am because I did.

And I spiral: "People are going to judge the fuck out of me. They're going to see it's not perfect. They're going to think I'm a fraud."

But here's what I'm learning: those highlight reels you're comparing yourself to? They're lies by omission. Every single one of those founders had a moment where they looked at their thing and thought "this isn't ready."

They shipped anyway. So will I.

The hate you're afraid of? Most of it is coming from inside your own head.`,

  polishedVersion: `"People are going to judge me harshly."

This thought has surfaced repeatedly as I prepare for launch. I study other product releases—polished landing pages, seamless demos, founders who project certainty.

My product has rough edges. The demo isn't perfect. Some elements were finished at the last minute.

The mental spiral begins: comparing my behind-the-scenes to everyone else's highlight reel.

Here's the reframe that's helping me: every founder I admire had a moment of "this isn't ready" right before they shipped. The difference is they chose action over perfection.

The harshest critic is usually internal. The audience is typically more forgiving than we imagine.

What comparison trap are you working to escape?`
};

// Post 3: Mental Warfare
const post3 = {
  title: "Post 3: The War Inside Your Head",
  theme: "Internal Battle / Fighting Your Programming / Technical Perfectionism",
  rawVersion: `Building a startup is 20% building and 80% mental warfare.

Nobody fucking tells you this.

You're not just fighting the market. You're not just fighting competitors. You're fighting your own goddamn programming.

Every limiting belief your parents gave you. Every time someone told you to "be realistic." Every failure that taught you to play it safe.

And then there's the technical spiral. You wake up, look at your code, and think: "Oh my god, the state management doesn't update anymore. The DAG I put together isn't shifting variables step-by-step. Holy fucking shit."

And suddenly you're not just questioning your code. You're questioning everything.

"What about my core offering? What about my core message? If THAT'S not right, nobody will understand the product."

"Will users even get it? Is the interface clear enough? Will they hate it?"

All of that shows up when you try to do something new. And it doesn't show up politely. It shows up at 3am when you can't sleep. It shows up when you're about to hit publish. It shows up when someone asks "so what do you do?"

The startup journey is really a journey of reprogramming your own mind while simultaneously building a product.

And the crazy part? You have to do both at the same time. While paying rent.

If you're in the middle of this mental war right now: you're not crazy. You're not alone. This is the work.`,

  polishedVersion: `Building a company involves a ratio I wasn't prepared for: roughly 20% actual building, 80% managing your own psychology.

You're not just competing in a market. You're actively working against your own conditioning.

Years of "be realistic" advice. Past experiences that taught caution. Internalized beliefs about what's possible for someone like you.

And then there's the technical perfectionism spiral. You review your code and discover something isn't working as expected. State isn't updating. Logic isn't flowing correctly.

Suddenly you're not just questioning that one component. You're questioning everything.

"Is my core value proposition clear enough?"
"Will users understand what this does?"
"If the foundation is shaky, does anything else matter?"

These patterns surface at inconvenient moments—late nights, right before you publish something, when someone asks about your work.

The startup journey is simultaneously a product development journey and a personal development journey. They can't be separated.

If you're experiencing this internal tension: it's not a sign something's wrong. It's part of the process. This is the work most people never see.`
};

// Post 4: The Unglamorous Reality
const post4 = {
  title: "Post 4: The Shit Nobody Posts About",
  theme: "Bugs, Errors, The Perfectionism Loop, Delayed Launches",
  rawVersion: `Let me tell you about my Tuesday.

6am: Woke up to a bug that broke the entire checkout flow.
8am: Fixed it. Broke something else.
11am: Finally working. Realized my demo video was garbage.
2pm: Re-recorded the demo. Voice sounded dead inside.
4pm: Said fuck it, used an AI voiceover.
6pm: AI voiceover sounded weird. Recorded it myself again.
9pm: Good enough. Hit export.
11pm: Realized I forgot to update the pricing page.
1am: Done. Looked at the clock. Felt nothing.

And here's what happens the next morning:

"Oh my god, did I check the onboarding again?"
"Shit, that's the 20th bug I found. I can't release this."

And just like that, you've delayed another two weeks. Two weeks you probably didn't need to delay.

We see the highlight reels: "Inside of 20 days I got a million followers and now I'm a millionaire." Or: "Grinding on my side project and crushing it."

But where's the war? Where's the mental agony of finding ANOTHER bug? The spiral of "it's so broken" when you look at it fresh?

The reality is some people didn't go through this war. Some people were trained for what they're doing. They had the skills already. They had the confidence already.

But most of us? We're fighting perfectionism while the clock ticks. We're finding one more thing to fix. We're telling ourselves "just one more week" for the tenth time.

If your journey looks like this: welcome to the club. The membership fee is your sanity.`,

  polishedVersion: `A recent day in my building journey:

Early morning: discovered a critical bug. Fixed it, which created a new issue.
Midday: finally stable. Realized supporting content needed to be redone.
Afternoon: re-created it. Quality wasn't there. Tried a different approach.
Evening: iterated three more times until acceptable.
Late night: finished. Found one more thing that needed updating.
After midnight: actually done.

And then the next morning: "Did I verify the onboarding flow?" "That's the twentieth issue I've found. I can't release this."

And suddenly, two more weeks have passed. Two weeks that probably weren't necessary.

The public narrative looks different: "Built this in 20 days, massive traction." The grind aesthetics. The success metrics.

But where's the actual struggle? The mental weight of discovering another problem? The fresh-eyes panic when you review your own work?

Some builders didn't experience this war. They had relevant training. They had the skills and confidence pre-loaded.

But many of us are fighting perfectionism against deadlines. Finding one more thing to address. Telling ourselves "one more week" repeatedly.

If your process looks unglamorous: you're doing it right. The highlight reel comes later—if it comes at all.`
};

// Post 5: Am I Stealing Money?
const post5 = {
  title: "Post 5: The Fear of Taking People's Money",
  theme: "Charging / Value / Fraud Feelings",
  rawVersion: `I'm about to charge money for something I built.

And part of me feels like a thief.

"Is this good enough to charge for?"
"Am I going to disappoint people?"
"What if they want a refund?"
"What if I'm just... taking their money for something half-baked?"

This is the imposter syndrome nobody talks about. Not just "am I good enough" but "am I allowed to exchange value for money?"

Here's what I'm telling myself: if someone pays for your thing and gets value from it, you haven't stolen anything. You've created a transaction that benefits both people.

The fear of taking money is really the fear of being judged. Of having your work measured in dollars. Of someone saying "this wasn't worth it."

But you know what's worse than that fear? Never knowing if people would have paid. Never testing the value you've created.

I'm charging for my thing. It might not be perfect. But it's real and it solves a real problem.

That's worth something.`,

  polishedVersion: `I'm preparing to charge for something I've built, and an unexpected fear has surfaced.

Not imposter syndrome about my skills—but something adjacent: am I creating enough value to justify the exchange?

"Is this worth the price?"
"What if users are disappointed?"
"What if I'm not delivering enough?"

This is a common founder fear that's rarely discussed openly. The transition from "free thing I made" to "paid product with expectations."

The reframe that's helping: if someone purchases your product and receives value from it, both parties benefit. That's not extraction—that's exchange.

The alternative—never testing whether people would pay—means never validating your work in the most honest way possible.

I'm moving forward with pricing that reflects the value I believe I'm creating. It may not be perfect yet. But it's real and it addresses a real problem.`
};

// Post 6: The Odds
const post6 = {
  title: "Post 6: You Might Not Make It",
  theme: "Realistic Odds / Doing It Anyway",
  rawVersion: `Here's the truth nobody wants to say out loud:

You might not make it.

Statistically, most startups fail. Most products nobody buys. Most launches get 12 upvotes and disappear into the void.

You can do everything right and still lose.

I know this. I've read the stats. I've seen friends try and fail. I've failed before myself.

And I'm doing it anyway.

Not because I'm delusional. Not because I think I'm special. But because the alternative—not trying—guarantees failure.

At least this way I get to find out. I get to test my ideas against reality. I get to know if I could have made it.

The odds are not in your favor. That's true. But the people who beat the odds aren't the ones who had better odds. They're the ones who kept playing.

Fuck the odds. Let's find out.`,

  polishedVersion: `A truth that's uncomfortable to state directly:

Most new products fail. Most launches don't gain traction. The statistical odds of meaningful success are genuinely low.

I'm aware of this. I've seen the data. I've watched peers try and not succeed. I've experienced failure personally.

And I'm proceeding anyway.

Not from naivety or a belief that I'm exceptional. But from a simple calculation: not attempting guarantees the outcome I'm trying to avoid.

By trying, I at least get data. I get to test assumptions against reality. I get to learn what's actually possible.

The people who achieve unlikely outcomes aren't those who had better odds. They're often the ones who persisted through unfavorable odds.

Awareness of the difficulty doesn't require surrender to it.`
};

// Post 7: Thinking Positive Because You Have To
const post7 = {
  title: "Post 7: You Cannot Create a Positive Life Thinking Negative",
  theme: "Mindset / Positive Thinking as Survival",
  rawVersion: `I used to roll my eyes at "positive thinking" stuff.

Sounded like toxic positivity. Like ignoring real problems. Like lying to yourself.

But building this thing has taught me something: you literally cannot create something positive while thinking negative.

Not philosophically. Practically.

When I'm in a negative headspace, I don't ship. I don't create. I scroll Twitter and compare myself to people doing better than me.

When I force myself to think "okay, what CAN work here?"—even when everything feels broken—I actually move forward.

Positive thinking isn't about pretending everything is fine. It's about choosing to focus on what you can control when everything feels out of control.

It's a survival mechanism. It's the thing that keeps you building when the voice in your head says "give up."

I'm not naturally optimistic. But I'm training myself to be. Because the alternative doesn't build products.

What's one thing you can choose to focus on today that moves you forward?`,

  polishedVersion: `I used to be skeptical of "positive mindset" advice.

It felt like ignoring real challenges. Like forced optimism. Like self-deception.

Building has shifted my perspective—not philosophically, but practically.

When I'm operating from a negative mental state, output drops significantly. Creation stalls. Time gets spent on comparison rather than progress.

When I deliberately shift to "what can work here?"—even when things feel broken—forward motion resumes.

Positive thinking, as I now understand it, isn't about denying difficulty. It's about directing attention toward what you can influence when much feels outside your control.

It's a practical tool. It's what sustains building when every signal says to stop.

I'm not naturally inclined toward optimism. But I'm developing it as a skill. Because the alternative doesn't produce results.

What's one thing within your control that could move you forward today?`
};

// Post 8: The Moment It Hit Me
const post8 = {
  title: "Post 8: I Was Wrong About the Hate",
  theme: "Launch Day / Fear vs Reality / Emotional Release",
  rawVersion: `I launched on Product Hunt today.

For weeks, I've been writing about the fear. The voice that says "people are going to hate you." The spiral of "it's not ready." The mental warfare of shipping something imperfect.

I hit publish. I braced myself.

Then someone found my account. Someone I didn't know. And they just... gave me love. "Congrats on the launch." Pure support. No judgment. No hate.

And I fucking broke down.

I'm talking tears. Real ones. The kind you don't expect.

All those weeks of "people are going to hate me." All that mental agony. All that fear of judgment.

And the first real feedback I got was kindness.

I was wrong.

The hate I was so afraid of? It was mostly in my own head. The audience I imagined tearing me apart? They were rooting for me.

I don't know if this product will succeed. I don't know if the numbers will be good. But I know this:

The fear was a liar.

If you're holding back because you think people will hate you: you're probably wrong too.

Ship it. Find out.`,

  polishedVersion: `I launched today.

For weeks leading up to this, I've been processing the fear. The internal voice predicting harsh judgment. The anxiety about putting imperfect work into the world.

I published. I prepared for criticism.

What I received was support. Someone reached out with genuine congratulations. Pure encouragement. No conditions attached.

I got emotional. More than I expected.

All those weeks of anticipating negativity. All that energy spent on worst-case scenarios. All that fear of how people would respond.

And the first real interaction was kindness.

The fear, it turns out, was mostly internal. The critical audience I imagined didn't materialize. People were supportive.

I don't know yet whether this will succeed commercially. The metrics will take time.

But I learned something important: the fear was disproportionate to reality.

If you're delaying because you expect hostility — consider that you might be wrong.

The audience is often kinder than we imagine.`
};

// Calendar - POST-LAUNCH VERSION (Lead with the payoff, then tell the backstory)
const calendar = [
  { week: 1, day: "Today (Sat)", post: "Post 8: I Was Wrong About the Hate", platforms: "X (raw), LinkedIn (polished) — THE HOOK" },
  { week: 1, day: "Sunday", post: "Post 1: The Voice That Says You're Not Ready", platforms: "X (raw), Reddit r/Entrepreneur — backstory begins" },
  { week: 1, day: "Monday", post: "Post 2: People Are Going to Hate Me", platforms: "X (raw), LinkedIn (polished)" },
  { week: 1, day: "Tuesday", post: "HN Show HN Post", platforms: "Hacker News — technical audience" },
  { week: 1, day: "Wednesday", post: "Post 3: Mental Warfare", platforms: "X (raw), Indie Hackers (polished)" },
  { week: 1, day: "Thursday", post: "Post 4: The Unglamorous Reality", platforms: "X (raw), Reddit r/startups (raw)" },
  { week: 1, day: "Friday", post: "Post 5: Taking People's Money", platforms: "X (raw), LinkedIn (polished)" },
  { week: 2, day: "Monday", post: "Post 6: The Odds", platforms: "X (raw), Indie Hackers (polished)" },
  { week: 2, day: "Wednesday", post: "Post 7: Positive Thinking", platforms: "X (raw), LinkedIn (polished)" },
  { week: 2, day: "Ongoing", post: "Product Hunt momentum + engagement", platforms: "Reply to comments, share updates, cross-promote" }
];

// Build the document
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 48, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 400, after: 200 } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 300, after: 150 } } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "444444" },
        paragraph: { spacing: { before: 200, after: 100 } } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      // Title Page
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(seriesTitle)] }),
      new Paragraph({ children: [new TextRun({ text: seriesTagline, italics: true, size: 28 })] }),
      new Paragraph({ spacing: { before: 200 }, children: [new TextRun({ text: "An 8-Post Content Series by Kevin", size: 24 })] }),
      new Paragraph({ spacing: { before: 100 }, children: [new TextRun({ text: "For: X (Twitter), Reddit, LinkedIn, Indie Hackers", size: 22, color: "666666" })] }),

      new Paragraph({ children: [new PageBreak()] }),

      // Table of Contents
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Contents")] }),
      new Paragraph({ spacing: { before: 100, after: 80 }, children: [new TextRun("1. The Voice That Says You're Not Ready")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("2. People Are Going to Hate Me")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("3. The War Inside Your Head")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("4. The Shit Nobody Posts About")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("5. The Fear of Taking People's Money")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("6. You Might Not Make It")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("7. Positive Thinking as Survival")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("8. I Was Wrong About the Hate")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("9. Content Calendar")] }),

      new Paragraph({ children: [new PageBreak()] }),

      // Post 1
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(post1.title)] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: `Theme: ${post1.theme}`, italics: true, color: "666666" })] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Raw Version (X, Reddit)")] }),
      ...post1.rawVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Polished Version (LinkedIn, Indie Hackers)")] }),
      ...post1.polishedVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ children: [new PageBreak()] }),

      // Post 2
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(post2.title)] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: `Theme: ${post2.theme}`, italics: true, color: "666666" })] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Raw Version (X, Reddit)")] }),
      ...post2.rawVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Polished Version (LinkedIn, Indie Hackers)")] }),
      ...post2.polishedVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ children: [new PageBreak()] }),

      // Post 3
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(post3.title)] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: `Theme: ${post3.theme}`, italics: true, color: "666666" })] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Raw Version (X, Reddit)")] }),
      ...post3.rawVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Polished Version (LinkedIn, Indie Hackers)")] }),
      ...post3.polishedVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ children: [new PageBreak()] }),

      // Post 4
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(post4.title)] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: `Theme: ${post4.theme}`, italics: true, color: "666666" })] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Raw Version (X, Reddit)")] }),
      ...post4.rawVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Polished Version (LinkedIn, Indie Hackers)")] }),
      ...post4.polishedVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ children: [new PageBreak()] }),

      // Post 5
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(post5.title)] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: `Theme: ${post5.theme}`, italics: true, color: "666666" })] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Raw Version (X, Reddit)")] }),
      ...post5.rawVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Polished Version (LinkedIn, Indie Hackers)")] }),
      ...post5.polishedVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ children: [new PageBreak()] }),

      // Post 6
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(post6.title)] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: `Theme: ${post6.theme}`, italics: true, color: "666666" })] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Raw Version (X, Reddit)")] }),
      ...post6.rawVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Polished Version (LinkedIn, Indie Hackers)")] }),
      ...post6.polishedVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ children: [new PageBreak()] }),

      // Post 7
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(post7.title)] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: `Theme: ${post7.theme}`, italics: true, color: "666666" })] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Raw Version (X, Reddit)")] }),
      ...post7.rawVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Polished Version (LinkedIn, Indie Hackers)")] }),
      ...post7.polishedVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ children: [new PageBreak()] }),

      // Post 8
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(post8.title)] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: `Theme: ${post8.theme}`, italics: true, color: "666666" })] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Raw Version (X, Reddit)")] }),
      ...post8.rawVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Polished Version (LinkedIn, Indie Hackers)")] }),
      ...post8.polishedVersion.split('\n').map(line =>
        new Paragraph({ spacing: { after: 120 }, children: [new TextRun(line || " ")] })
      ),

      new Paragraph({ children: [new PageBreak()] }),

      // Content Calendar
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Content Calendar: 3-Week Push")] }),
      new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "Schedule for maximum engagement leading up to launch", italics: true, color: "666666" })] }),

      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        columnWidths: [1500, 1800, 3000, 3060],
        rows: [
          new TableRow({
            children: [
              new TableCell({ borders, shading: { fill: "2D3748", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Week", bold: true, color: "FFFFFF" })] })] }),
              new TableCell({ borders, shading: { fill: "2D3748", type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Day", bold: true, color: "FFFFFF" })] })] }),
              new TableCell({ borders, shading: { fill: "2D3748", type: ShadingType.CLEAR }, width: { size: 3000, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Post", bold: true, color: "FFFFFF" })] })] }),
              new TableCell({ borders, shading: { fill: "2D3748", type: ShadingType.CLEAR }, width: { size: 3060, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Platforms", bold: true, color: "FFFFFF" })] })] }),
            ]
          }),
          ...calendar.map((row, i) => new TableRow({
            children: [
              new TableCell({ borders, shading: { fill: i % 2 === 0 ? "F7FAFC" : "FFFFFF", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun(`Week ${row.week}`)] })] }),
              new TableCell({ borders, shading: { fill: i % 2 === 0 ? "F7FAFC" : "FFFFFF", type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun(row.day)] })] }),
              new TableCell({ borders, shading: { fill: i % 2 === 0 ? "F7FAFC" : "FFFFFF", type: ShadingType.CLEAR }, width: { size: 3000, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun(row.post)] })] }),
              new TableCell({ borders, shading: { fill: i % 2 === 0 ? "F7FAFC" : "FFFFFF", type: ShadingType.CLEAR }, width: { size: 3060, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun(row.platforms)] })] }),
            ]
          }))
        ]
      }),

      new Paragraph({ spacing: { before: 400 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Platform Notes")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: "X (Twitter)", bold: true }), new TextRun(": Use raw version. Thread format works well. End with a question for engagement.")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: "Reddit", bold: true }), new TextRun(": Raw version. Best subreddits: r/Entrepreneur, r/startups, r/SideProject. Self-posts only, no links in body.")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: "LinkedIn", bold: true }), new TextRun(": Polished version. Add line breaks for readability. Professional but human.")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: "Indie Hackers", bold: true }), new TextRun(": Polished version. Community appreciates vulnerability + lessons learned.")] }),

      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_3, children: [new TextRun("Engagement Tips")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun("1. Respond to every comment in the first 2 hours")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun("2. End posts with a question to boost engagement")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun("3. Cross-reference your other posts (\"I wrote about this yesterday...\")")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun("4. Share screenshots of drafts/behind-the-scenes as supplementary content")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun("5. Week 3 is launch week\u2014tease the product in Posts 5-7")] }),
    ]
  }]
});

// Generate the document
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/sessions/adoring-youthful-cerf/mnt/senior-sandbox/senior_sandbox/docs/marketing/The-Mental-Game-Content-Series.docx", buffer);
  console.log("Document created successfully!");
});
