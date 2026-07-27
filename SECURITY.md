# Security policy

## Reporting a vulnerability

Please do **not** open a public issue for credential exposure, unsafe file handling, arbitrary code execution, dependency compromise, or another exploitable security problem.

Use GitHub's **Report a vulnerability** button under the repository Security tab (private vulnerability reporting). Include:

- affected version and operating system;
- impact and realistic attack conditions;
- minimal reproduction steps or proof of concept;
- suggested mitigation, if known.

You should receive an acknowledgement within 3 business days and a status update within 10 business days. Please allow a reasonable remediation window before public disclosure.

## Supported versions

Security fixes target the latest tagged release and the `main` branch.

## Credential safety

Provider keys are loaded from the local `.env` file and must never be committed. If a real key is ever pushed—even briefly—revoke it at the provider immediately. Removing the file from the latest commit does not remove it from Git history.

