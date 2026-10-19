# Language

Every language rule for this skill, in one place. It applies to every word a reader or the user sees: `draft.md`, titles, digest, `notes.md`, and questions to the user. `scripts/lint.py` reads the two word lists in § 7 from this file, so editing them here changes what lint checks.

When the user decides something about wording that holds for all articles, record it in the relevant section with the date.

## 0. Core rule

Write idiomatic Chinese. Be precise and concise: no rambling, no filler. (2026-10-19)

- **Natural Chinese.** Write the way a Chinese researcher writes, not the way English reads when translated: Chinese word order, Chinese collocations, no calqued nouns (§ 6).
- **Precise.** Each sentence says exactly what the source supports, no more and no less (§ 5). Prefer the specific word over the general one, and a number over an adjective.
- **Concise.** Every sentence must carry information the reader does not already have. Cut sentences that announce, restate, or pad; cut a clause when the sentence means the same without it. If a paragraph can lose a sentence without losing content, it loses it (§ 4, § 6).

The sections below spell this rule out. When a case is not covered, apply this rule.

## 1. Chinese and English

- Narrative in Simplified Chinese.
- Keep in original English, never translated or transliterated: method, tool, package and model names; gene, protein, dataset and accession IDs; person names; journal names; paper titles; file formats; URLs and DOIs; statistics terms readers know in English (`p-value`, `AUC`).
- No English adjectives or verbs inside Chinese sentences (`这个 idea 很 elegant`). English nouns from the list above are fine.

## 2. Terms

- English names drop in without translation. Add a short Chinese gloss in parentheses only for something genuinely obscure to this audience: `Harmony（单细胞批次校正方法）`. Common terms (`UMAP`, `scRNA-seq`, `PCA`) get none.
- Concepts the paper coins (e.g. tipping point, PMD, pClone, CMF) get a short Chinese gloss at first use and stay in English afterwards. (2026-10-18)
- After first mention, always the English form; never introduce a Chinese alias midway.
- Inline single symbols in unicode (`Σ`, `α`, `≤`). WeChat does not render LaTeX; a formula is prose or an image.

## 3. Voice and reference

- Third person. No 我 / 我们 / 你. Refer to the work as 作者、研究者、该研究.
- First mention of the authors: `<机构> <PI 英文名> 等在 <期刊或预印本> 发表了题为 <English title> 的研究文章`. Afterwards `<First author 英文姓> 等` or 作者.
- Outside work cited inline: `Trapnell et al. Nature Biotechnology 2014`.
- No emoji, no rhetorical questions in the body. Analogies only when a neighboring-field reader would otherwise be lost, with the analogy's limit stated.

## 4. Sentences and paragraphs

- Sentences of roughly 25–60 汉字, one idea each.
- Connectives (然而、因此、此外、进一步、由此) where the logic needs them, not as decoration and never two in a row.
- Paragraphs of three to six sentences, one step of the argument each, at most about 250 汉字 so they read well on a phone.
- Tight prose: no sentences announcing the article's structure, no repeated listing of points already made, no padding. (2026-10-19)

## 5. Evidence wording

The wording must claim exactly what the source claims.

- 显著 only when the paper reports a test. A numeric comparison without a test is 高于 / 低于. A visible direction without numbers is 呈……趋势.
- No degree word the source lacks: 明显、显著、大幅、远高于.
- Hedges carry over: suggests → 提示, may → 可能, we propose → 作者提出. What the paper leaves open stays open.
- Relations are stated as the source states them. "A and B are hard to achieve together" is not "A destroys B". "The authors speculate X" is not "X is confirmed". "Confirmed to exist" and "possibly committed to a lineage" are different claims and stay separate.
- Dataset-specific results stay dataset-specific: 在 <dataset> 上, not 普遍适用.
- 首次 / 第一个 / state-of-the-art only when the paper names the comparison, and then attributed: 作者将其定位为相对 X 的改进.

## 6. Translationese and filler

- No nouns calqued from English: representation is not 表征 (use 刻画、占比、组成), signature is not 签名 (特征), coherent is not 连贯的 (紧凑的、一致的). No "……之间的一个可测量的权衡".
- No English clause order: a modifier longer than about 25 characters before its noun becomes its own clause; the subject comes early.
- No filler: 本文将按……顺序解读; 值得一提的是 used as a connective; 综上所述 outside the conclusion; a closing sentence that restates its own paragraph.

## 7. Word lists (read by lint)

Each backticked item under these two headings is checked against the draft body. Both produce warnings, not errors.

### Banned

Marketing and unsourced superlatives; remove them.

`震惊` `重磅` `炸裂` `颠覆` `革命性` `赋能` `黑科技` `史无前例` `前所未有` `首次` `有望成为` `或将` `unprecedented` `first-ever` `revolutionize`

### Check

Translationese and filler seen in reviewed drafts. Some uses are legitimate; judge each hit.

`表征` `签名` `连贯的区块` `可测量的权衡` `值得一提的是` `众所周知` `本文将` `本文按` `本文沿着` `下面我们来看` `接下来我们看` `综上所述`

## 8. Repo-tutorial articles

Repo-only articles (`mode-repo.md`) differ from § 3–4 in these points only:

- 我们 is acceptable in instructional steps (这里我们选择……); 你 only in caveats about the reader's own data.
- Shorter sentences (15–40 汉字), fewer connectives, paragraphs of one to three sentences between code blocks.
- Method names in their exact API form (`st.tl.Niche_Model`); parameters as inline code (`n_neighbors=15`). Code comments may be short Chinese.
- Cite the example dataset: `示例数据来源于 Wei et al. Science 2022`.
