---
slug: pochemu-bas-ploho-zvuchit-v-mikse
title: Why your bass sounds bad in the mix (and how to fix it)
title_tag: Why your bass sounds bad in the mix — Podlesny Twins
description: Bass vanishing on phones or booming in the club? The working range, harmonics, checking the sub without a subwoofer, the kick clash and two mistakes that wreck the low end.
date: 2026-10-01
lead: Low-end problems usually come from a badly chosen key, and it's not just the key: the register the bass sits in matters too. The working range is F1 to A1 (a fundamental of roughly 44–55 Hz, and on a phone you hear its harmonics): a bass there comes through on headphones, in a club and on a phone. Below that it disappears without a big subwoofer, and above 80 Hz it runs short of sub.
tags: bass, 808, sub, harmonics, sidechain, kick
sources:
  - 607 | 2026-08-30 | Why does the bass sound bad in the mix? Part 1
  - 55 | 2021-05-11 | An 808 bass trick
  - 67 | 2021-07-28 | What we noticed mixing bass with the kick
---

![A joke book cover, "The Theory of the Low End" by P. K. Podlesny and A. K. Podlesny](/blog/img/bas-teoriya-nizkogo-kontsa.jpg "The picture that went with our channel post about bass")

## It starts with the key

Low-end problems usually come from a badly chosen key. That's not only about a bass that's out of key: the range the instrument plays in matters too. The working range for a bass is F1 to A1. A bass there can be heard on headphones, in a club and on a phone. Lower down, closer to C1 (32.7 Hz), it disappears unless the listener has a serious subwoofer.

## Why can't I hear the bass on a phone?

Everything below 50 Hz is the range that hits you in the chest. It's hard to hear at home; you notice it in a club, at a concert or in a good studio. It's a physical sensation of low end, and for most listeners it simply doesn't exist, because their speakers and headphones don't reproduce it.

Instead of the sub, a phone speaker, headphones or a small Bluetooth speaker give you the bass's harmonics. If the 808's fundamental is around 40 Hz (roughly E1), what you hear is 80, 120, 160 Hz and up.

## A bass that's too low: work the harmonics

With a bass that's too low, the only way to make it translate is to create or boost the second and third harmonics and pull down the fundamental, so smaller systems have something to play. Psychoacoustics helps too: when the harmonics are there, the brain fills in the sub.

Don't overdo the harmonics either. The second, third and fourth give the bass its body and weight, but overdo them and it gets muddy and woolly. That's easy to do with bass enhancers, saturators and other drive plugins, so it pays to compare the harmonic balance against a reference. The reference might, say, have the third harmonic noticeably up and the second carefully tucked away.

There's a catch. A bass rarely sits on one note, and when the note changes, all the harmonics move with it. This is where [SurferEQ by Sound Radix](https://www.soundradix.com/products/surfereq/) helps us a lot: it tracks the pitch and moves the EQ bands along with the melody. The developers promise that "it all just works". In practice it's not magic: on instruments with a busy spectrum, and especially on the master bus, the tracking gets weird, but on an 808 it works great.

## A bass that's too high: no sub

If the bass sits above the optimal range, from 80 Hz up, there's little or no sub content. If there's no sub, you can't EQ it up. In that case let the kick carry the sub, or generate lower harmonics with a plugin like [MBassador](https://www.wavesfactory.com/audio-plugins/mbassador/).

## Working with the sub when you can barely hear it

You can check everything below 50 Hz in Realphones by [dSONIQ](https://www.dsoniq.com/). Its Club mode simulates a club sound system: it boosts and extends the low end. Problems show up right away. The track sounds empty if there's no sub, muddy if there's too much, and an overly long kick turns into a constant drone.

## What if there's too much sub?

The standard fix is EQ. Clean the sub out of anything that doesn't need it, even the kick or the bass if you decide one of them can do without.

If the problem isn't the amount of sub but how it interacts with the rest of the arrangement, look at how long the low frequencies ring, especially in the kick. The kick's tail can clash with the bass, because that tail is where the boom and the kick's note live. You can shorten the kick with a transient shaper or pick a different sample. And if the kick is carrying the sub, sidechain the bass to it, so the bass stops droning nonstop and starts pushing the rhythm.

## What we noticed mixing bass with the kick

We had a period when we thought we'd finally figured out kick and bass. We measured the kick's length in milliseconds and ducked the bass whenever the kick played (with ShaperBox 2). We liked working with numbers and analyzers so much that we put an oscilloscope on the group to watch the sidechain timing and the phase down there. On a lot of tracks this worked great and gave us a solid low end.

The moral of the story: we later found plenty of tracks where the method worked badly, even though everything looked perfect on the meters, graphs and numbers. Sometimes sidechaining does nothing except kill the bass's attack and the whole punch with it. When a track needs that punch, we solve the clash another way: with EQ, compression or plain balance.

## Two mistakes that can ruin everything

1. You saturated the bass hard and forgot to check what happened in the low and high mids. Harmonics can clash, and the top end of heavy saturation turns into noise that gets in the way of the vocal and everything else up there.
2. You chased more sub and ignored the mids and highs. The more bass there is, the more the mix needs top end. Without it you lose balance and context, the bass sits apart from the mix and turns into mud and empty boom.

Bass shows up in our tier list too: we put [mono on the very bottom](/en/tier/#bass-mono) in S because it makes the mix translate, and [splitting the bass into bands](/en/tier/#bass-split-bands) only in B, because of phase problems. And if the kick has no attack on top of that, see [our piece on transients](/en/blog/tranzienty-v-svedenii/).

## FAQ {#faq}

### Why can I hear the bass on monitors but not on my phone?

A phone speaker can't reproduce the sub; everything below 50 Hz simply isn't there for it. You only hear the bass's harmonics: for a 40 Hz fundamental that's 80, 120, 160 Hz and up. If the bass is too low and the harmonics are weak, it disappears. Then we boost the second and third harmonics and pull down the fundamental.

### Can I bring the sub up with an EQ?

Only if it's in the sound to begin with. If the bass plays above 80 Hz, there's little or no sub content in it, and there's nothing for the EQ to lift. In that case we let the kick carry the sub, or generate lower harmonics with a plugin like MBassador.

### Should the bass be in mono?

Yes, but only the very bottom, roughly below 100–150 Hz. Everything above that can be wider. Mono down there makes the mix translate, which is why it's S tier in our tier list.
