// @ts-check
/**
 * lib/matching/deterministic-scorer.mjs
 * Computes deterministic, explainable, weighted match scores before LLM evaluation.
 */

/**
 * Common tech & domain taxonomy dictionaries for keyword identification.
 */
const DOMAIN_KEYWORDS = {
  genai: ['llm', 'genai', 'generative ai', 'rag', 'langchain', 'langgraph', 'llamaindex', 'agentic', 'agents', 'embeddings', 'transformer', 'prompt engineering', 'fine-tuning', 'rlhf', 'vllm', 'ollama'],
  ml: ['machine learning', 'deep learning', 'pytorch', 'tensorflow', 'scikit-learn', 'nlp', 'computer vision', 'pandas', 'numpy', 'model deployment', 'mlops', 'feature store'],
  backend: ['python', 'fastapi', 'node.js', 'typescript', 'go', 'golang', 'rust', 'java', 'c++', 'distributed systems', 'grpc', 'graphql', 'rest api', 'microservices'],
  cloud_infra: ['aws', 'gcp', 'azure', 'kubernetes', 'k8s', 'docker', 'terraform', 'ci/cd', 'kafka', 'redis', 'postgresql', 'vector db', 'pinecone', 'milvus', 'qdrant', 'chroma', 'weaviate'],
};

/**
 * Extracts candidate skills and preferences from profile object.
 * @param {object} profile
 * @returns {{ skills: string[], targetTitles: string[], targetArchetypes: string[], minYears: number }}
 */
function extractProfileCandidateSignals(profile = {}) {
  const skills = new Set();

  // Superpowers & proof points
  (profile.narrative?.superpowers || []).forEach((/** @type {string} */ s) => {
    s.split(/[,\s/]+/).forEach((tok) => tok.length > 2 && skills.add(tok.toLowerCase()));
  });

  // Target roles
  const targetTitles = (profile.target_roles?.primary || []).map((/** @type {string} */ t) => t.toLowerCase());
  const targetArchetypes = (profile.target_roles?.archetypes || []).map((/** @type {any} */ a) => (typeof a === 'string' ? a.toLowerCase() : (a.name || '').toLowerCase()));

  // Candidate explicit skills (if provided in profile.skills or candidate object)
  if (Array.isArray(profile.skills)) {
    profile.skills.forEach((/** @type {string} */ s) => skills.add(s.toLowerCase()));
  }

  return {
    skills: Array.from(skills),
    targetTitles,
    targetArchetypes,
    minYears: profile.candidate?.years_experience ?? 5,
  };
}

/**
 * Computes deterministic match between Job and Candidate Profile.
 *
 * @param {object} job - Canonical Job object
 * @param {object} profile - Candidate Profile (from config/profile.yml)
 * @returns {object} DeterministicMatch object
 */
export function scoreJobDeterministically(job, profile = {}) {
  const candidate = extractProfileCandidateSignals(profile);
  const text = `${job.role?.title || ''} ${job.description || ''} ${(job.requirements?.skills || []).join(' ')}`.toLowerCase();

  // 1. Technical Skills Score (30%)
  const jobSkills = new Set(
    (job.requirements?.skills || []).map((/** @type {string} */ s) => s.toLowerCase().trim())
  );

  // Scan text for tech domain matches
  Object.values(DOMAIN_KEYWORDS).flat().forEach((kw) => {
    if (text.includes(kw)) {
      jobSkills.add(kw);
    }
  });

  const matchedSkills = [];
  const missingSkills = [];

  jobSkills.forEach((skill) => {
    const isMatched = candidate.skills.some((cs) => cs.includes(skill) || skill.includes(cs)) ||
      // Fallback: common foundational keywords if mentioned in superpowers/headline
      (profile.narrative?.headline || '').toLowerCase().includes(skill);

    if (isMatched) {
      matchedSkills.push(skill);
    } else {
      missingSkills.push(skill);
    }
  });

  const totalSkillCount = jobSkills.size || 1;
  const techSkillScore = Math.min(100, Math.round((matchedSkills.length / totalSkillCount) * 100));

  // 2. Experience & Seniority Alignment (20%)
  let seniorityScore = 70;
  const titleLower = (job.role?.title || '').toLowerCase();
  if (candidate.targetTitles.some((tt) => titleLower.includes(tt) || tt.includes(titleLower))) {
    seniorityScore = 95;
  } else if (candidate.targetArchetypes.some((ta) => titleLower.includes(ta) || ta.includes(titleLower))) {
    seniorityScore = 85;
  } else if (/lead|staff|principal|senior|architect/i.test(titleLower)) {
    seniorityScore = 80;
  }

  // 3. Domain Alignment (15% - GenAI / ML / High Value Tech)
  let domainScore = 50;
  const genAiHits = DOMAIN_KEYWORDS.genai.filter((kw) => text.includes(kw));
  if (genAiHits.length >= 3) {
    domainScore = 95;
  } else if (genAiHits.length >= 1) {
    domainScore = 80;
  }

  // 4. Cloud & Infrastructure Alignment (15%)
  const infraHits = DOMAIN_KEYWORDS.cloud_infra.filter((kw) => text.includes(kw));
  const infraScore = infraHits.length >= 3 ? 90 : (infraHits.length >= 1 ? 75 : 60);

  // 5. Location & Work Mode Fit (10%)
  let locationScore = 70;
  if (job.location?.remote) {
    locationScore = 95;
  } else if (job.location?.hybrid) {
    locationScore = 80;
  }

  // 6. Compensation Fit (10%)
  let compScore = 75;
  if (job.compensation?.max) {
    compScore = 85;
  }

  // Weighted aggregate
  const weightedOverall = Math.round(
    techSkillScore * 0.30 +
    seniorityScore * 0.20 +
    domainScore * 0.15 +
    infraScore * 0.15 +
    locationScore * 0.10 +
    compScore * 0.10
  );

  // Why it fits & gaps
  const whyItFits = [];
  if (seniorityScore >= 85) whyItFits.push(`Title matches target roles (${job.role?.title})`);
  if (genAiHits.length >= 2) whyItFits.push(`Strong GenAI/LLM domain focus (${genAiHits.slice(0, 3).join(', ')})`);
  if (matchedSkills.length > 0) whyItFits.push(`Aligned tech competencies: ${matchedSkills.slice(0, 4).join(', ')}`);
  if (job.location?.remote) whyItFits.push('Remote flexibility aligns with candidate preference');

  const risks = [];
  if (missingSkills.length > 0) risks.push(`Missing / unchecked keywords: ${missingSkills.slice(0, 3).join(', ')}`);
  if (!job.location?.remote && job.location?.onsite) risks.push(`On-site requirement in ${job.location.text}`);
  if (!job.compensation?.max) risks.push('Compensation not explicitly disclosed in posting');

  return {
    score: weightedOverall,
    confidence: 0.90,
    breakdown: {
      technicalSkills: techSkillScore,
      experienceSeniority: seniorityScore,
      domainAlignment: domainScore,
      cloudInfrastructure: infraScore,
      locationWorkMode: locationScore,
      compensationFit: compScore,
    },
    mustHaveMet: Math.max(1, matchedSkills.length),
    mustHaveTotal: Math.max(1, matchedSkills.length + missingSkills.length),
    matchedSkills: matchedSkills.slice(0, 10),
    missingSkills: missingSkills.slice(0, 10),
    genAiKeywords: genAiHits,
    infraKeywords: infraHits,
    whyItFits,
    risks,
    evaluatedAt: new Date().toISOString(),
  };
}

export default scoreJobDeterministically;
