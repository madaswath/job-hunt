// @ts-check
/**
 * plugins/sdk/permissions.mjs
 * Granular, Least-Privilege Permission Taxonomy for Job-hunt Plugins.
 */

export const PLUGIN_PERMISSIONS = {
  // Automated Safe Permissions (Can run autonomously)
  SEARCH_JOBS: {
    id: 'SEARCH_JOBS',
    name: 'Search Job Postings',
    description: 'Enables querying search results based on user criteria.',
    riskLevel: 'LOW',
  },
  READ_JOB_DETAILS: {
    id: 'READ_JOB_DETAILS',
    name: 'Read Job Descriptions',
    description: 'Retrieves full JD content and requirements.',
    riskLevel: 'LOW',
  },
  READ_JOB_ALERT_EMAILS: {
    id: 'READ_JOB_ALERT_EMAILS',
    name: 'Ingest Job Alert Emails',
    description: 'Reads incoming job notification emails from LinkedIn/Naukri/Indeed.',
    riskLevel: 'LOW',
  },
  CREATE_RECRUITER_DRAFT: {
    id: 'CREATE_RECRUITER_DRAFT',
    name: 'Create Outreach Drafts',
    description: 'Creates draft emails/messages without sending them.',
    riskLevel: 'LOW',
  },
  READ_REPLIES: {
    id: 'READ_REPLIES',
    name: 'Detect Inbound Replies',
    description: 'Matches incoming interview invites or recruiter replies to tracked jobs.',
    riskLevel: 'LOW',
  },
  SYNC_SAVED_JOBS: {
    id: 'SYNC_SAVED_JOBS',
    name: 'Import Saved Roles',
    description: 'Synchronizes roles bookmarked on third-party platforms into Job-hunt.',
    riskLevel: 'LOW',
  },

  // HIGH RISK: STRICTLY APPROVAL-GATED (NEVER RUNS AUTONOMOUSLY)
  SEND_RECRUITER_EMAIL: {
    id: 'SEND_RECRUITER_EMAIL',
    name: 'Send Recruiter Outreach (Human Approval Gated)',
    description: 'Sends email to recruiter ONLY after explicit user confirmation in the Approval Queue.',
    riskLevel: 'HIGH',
    requiresApproval: true,
  },
  SUBMIT_APPLICATION: {
    id: 'SUBMIT_APPLICATION',
    name: 'Submit Job Application (Human Approval Gated)',
    description: 'Final application submission ONLY after user reviews and approves.',
    riskLevel: 'HIGH',
    requiresApproval: true,
  },
};

/**
 * Validates whether requested permissions are compliant with least-privilege policy.
 * @param {string[]} requestedPermissions
 * @returns {{ valid: boolean, sanitized: string[], requiresApprovalFlags: string[] }}
 */
export function validatePluginPermissions(requestedPermissions = []) {
  const sanitized = [];
  const requiresApprovalFlags = [];

  for (const perm of requestedPermissions) {
    if (PLUGIN_PERMISSIONS[perm]) {
      sanitized.push(perm);
      if (PLUGIN_PERMISSIONS[perm].requiresApproval) {
        requiresApprovalFlags.push(perm);
      }
    }
  }

  return {
    valid: sanitized.length > 0,
    sanitized,
    requiresApprovalFlags,
  };
}

export default {
  PLUGIN_PERMISSIONS,
  validatePluginPermissions,
};
