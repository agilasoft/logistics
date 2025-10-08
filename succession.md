# PRODUCT SUCCESSION
June 30, 2025 Version
A Comprehensive Succession Plan for an Open-source Project

## Purpose and Scope 
CargoNext is an open-source logistics management platform that addresses freight forwarding, warehousing, transport, and customs operations. It is co-maintained by Opensource Support Phils., Inc. (OSSPH) and Agilasoft Cloud Technologies Inc. (Agilasoft). The purpose of this succession planning document is to guarantee uninterrupted stewardship, development, and support for CargoNext as a community-driven solution. This plan establishes mechanisms for governance, continuity of technical maintenance, secure release processes, knowledge transfer, documentation practices, infrastructure management, funding sustainability, and active community engagement.
By anticipating both planned and unplanned changes in leadership or maintainers, the project ensures long-term stability, resilience, and adherence to open-source values.

## Governance and Ownership 
CargoNext follows a co-maintainer model. OSSPH and Agilasoft share equal responsibility for both technical and service roles. Governance is exercised through a Steering Committee composed of at least two representatives from OSSPH, two from Agilasoft, and two elected members from the wider contributor community.
1.	Decision-Making: The preferred decision-making method is consensus. If consensus cannot be reached, decisions are made by majority vote of the Steering Committee. In the event of a tie, the wider contributor community may be consulted for an advisory vote.
2.	Licensing: CargoNext is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0+). This ensures that derivative works and modifications remain open-source and available to the community.
3.	Trademarks and Branding: The CargoNext brand and related marks are managed neutrally. No single organization can monopolize the use of the name, logo, or related branding. Policies on trademark usage are published to prevent misrepresentation.
4.	Contributor Ownership: Individual contributors retain copyright of their work, with contributions governed by Developer Certificate of Origin (DCO) or Contributor License Agreements (CLAs).

## Roles and Responsibilities 
Succession planning is effective only if responsibilities are clearly defined. CargoNext assigns the following roles:
•	Steering Committee (SC): Approves roadmaps, licensing changes, module ownership assignments, and handles emergency custodianship decisions.
•	Release Managers: Coordinate version cycles, maintain long-term support (LTS) branches, and ensure that updates are documented and stable.
•	Security Response Team (SRT): Monitors vulnerabilities, manages CVE disclosures, and executes rapid response patches.
•	Module Maintainers: Serve as custodians of functional areas such as Warehousing, Transport, Customs, or Infrastructure. Their tasks include reviewing pull requests, enforcing architecture standards, and maintaining module documentation.
•	Community Managers: Uphold the Code of Conduct, onboard contributors, moderate discussions, and facilitate events.
•	Infrastructure and DevOps Roles: Manage CI/CD pipelines, automate testing, enforce key rotation, maintain observability, and secure cloud infrastructure.

## Succession Triggers and Playbooks 
Succession can be triggered in three primary scenarios:
1.	Planned Departure: Maintainers provide at least 90 days’ notice. During this time, successors shadow the outgoing maintainer, documentation is updated, and responsibilities are gradually transferred.
2.	Unplanned Departure: Designated deputies or backup maintainers step in immediately. The Steering Committee convenes within seven days to formalize new ownership. Repository access keys and infrastructure credentials are rotated within 72 hours.
3.	Emergency Situations: In cases of severe security incidents, legal challenges, or other urgent threats, the Security Response Team takes operational control. If both co-maintainers are unavailable, the Steering Committee may assign an Emergency Custodian to safeguard the project until stability is restored.

## Handover Requirements 
To avoid disruption, a structured handover checklist is maintained:
1.	Repositories: Transfer GitHub organizational ownership, branch protections, and maintainers.
2.	Registries: Ensure control of PyPI, NPM, container registries, and rotate access tokens.
3.	Infrastructure: Document CI/CD pipelines, cloud accounts, build secrets, and observability endpoints.
4.	Domains and DNS: Maintain access to domain registrars, DNS records, and community mailing systems.
5.	Documentation: Update architectural decision records (ADRs), developer guides, runbooks, and release notes.
6.	Contracts and SLAs: Ensure professional services agreements, support commitments, and sponsorships are properly reassigned.

## Sustainability and Funding 
The project remains sustainable through a dual-track model:
•	Open-Source Core: CargoNext is free under AGPL-3.0+ and maintained by the community.
•	Professional Services: OSSPH, Agilasoft, and other qualified providers may offer commercial services such as training, deployments, integrations, or premium support.
•	Sponsorships and Grants: Neutral funding channels are established with transparency. All sponsorship funds are published publicly with clear allocation records.
•	Community Donations: Crowdfunding and voluntary contributions are encouraged to support infrastructure, documentation, and mentorship programs.

## Key Performance Indicators (KPIs) 
Succession planning effectiveness is measured through the following KPIs:
1.	Contribution Lead Time: Average time to merge pull requests or resolve issues.
2.	Release Cadence: Timely delivery of stable releases and LTS patches.
3.	Bus Factor Analysis: Number of active maintainers per module to mitigate dependency on single individuals.
4.	Security MTTR: Mean time to resolution for security vulnerabilities.
5.	Community Metrics: Growth in contributors, contributor retention rates, and inclusiveness of onboarding.
6.	Documentation Coverage: Percentage of modules with updated guides and ADRs.

## Review and Audits 
CargoNext succession planning undergoes:
•	Quarterly Operational Reviews: To ensure modules, processes, and maintainers are aligned with the roadmap.
•	Annual Governance Audits: Independent reviews of governance structures, licensing compliance, and funding transparency.
•	Incident Post-Mortems: Documented analysis of unplanned transitions or security incidents, ensuring lessons learned are incorporated into the plan.

## Summary
CargoNext is more than just a logistics platform; it is a community asset built on transparency, shared responsibility, and resilience. By adopting a comprehensive succession framework that addresses governance, technical maintenance, knowledge transfer, and sustainability, CargoNext can withstand leadership changes while remaining an enduring, open-source solution for the logistics industry. The adoption of the AGPL-3.0-or-later license guarantees that CargoNext will always remain free, open, and community-driven.

