# Dataset Card — VoxRubric Arabic-English Technical ASR Preservation Set

**Dataset ID:** `voxrubric-asr-preservation`  
**Version:** `1.0.0`  
**License:** Apache-2.0

## Purpose

This synthetic text benchmark tests whether ASR output preserves job-relevant technical speech, including Arabic/English code-switching and terms such as FastAPI, Redis, latency, and OpenTelemetry.

## Source policy

All reference and observed transcripts are hand-authored. The dataset contains no audio, voice biometrics, or real applicant data.

## Intended use

Use it to regression-test WER-derived word accuracy, critical-term recall, and mixed-script preservation.

## Out of scope

Do not use it to compare speakers, infer accent quality, or claim provider-level ASR accuracy.

## Limitations

Because it is text-only and synthetic, it does not represent acoustic conditions, dialect diversity, microphone artifacts, or natural disfluency.
