# Requirement Specifications

Essential requirements for &LIVING Buyer Matchmaking. These nine points prioritise the MVP's purpose, users, features, usability, data protection and unresolved decisions. Numbers refer to the original 27-point [Template][template] (pages 19-24). The full specification is in README.md.

## 1. The Purpose of the Project
Help compatible buyers combine their purchasing power to buy a home together, while generating qualified buyer groups and retaining customers within &LIVING.

**Missing:** measurable targets for successful matches, purchases and business value.

## 3. Users of the Product
The primary users are prospective co-buyers, especially younger and first-time buyers who cannot afford their preferred home alone. &LIVING agents receive qualified buyer groups.

**Missing:** validated co-buyer personas and agent workflows. The existing repeat-buyer audience in BMC and couples prioritised in SMP do not fully define this new audience.

## 4. Requirements Constraints
The platform must fit &LIVING's existing ecosystem and connect to its CRM and property databases.

**Missing:** confirmed API access, budget, delivery date, team capacity and technology restrictions.

## 8. The Scope of the Product
The MVP covers buyer profiles, matching, shared property search, messaging, shortlists and viewing requests. Property searches use &LIVING's portfolio, potentially including properties not publicly marketed (skuffesager). Loan approval, ownership contracts and transaction completion are not specified as MVP functions.

**Missing:** how buyers form or leave a group, and whether skuffesager will be available.

## 9. Functional and Data Requirements
* **Profiles:** collect budget, pre-approved loan amount, down payment, preferred location, property type, minimum area, acceptable transport time and lifestyle preferences.
* **Buyer matching:** calculate compatibility scores using financial compatibility and lifestyle alignment.
* **Property matching:** combine a formed group's purchasing power and find properties matching its budget and space requirements.
* **Messaging:** allow matched users to communicate securely before sharing personal contact details.
* **Shared shortlists:** allow buyers to save, vote on and discuss properties together.
* **Viewing requests:** submit requests for open houses or private viewings through the shared profile.

**Missing:** matching weights and thresholds, financial verification, group size, field validation, a data model and booking confirmation rules.

## 11. Usability and Humanity Requirements
Proposed: make profiles, match results and next steps easy to understand, with relevant information gathered together. In the survey, 38 of 45 respondents rated having information in one place at 4 or 5.

**Missing:** accessibility criteria, usability testing and measurable task-completion targets.

## 15. Security Requirements
Protect financial and lifestyle data through robust encryption, explicit consent flows and secure messaging.

**Missing:** authentication, access permissions, which details other buyers and agents can see, and incident handling.

## 17. Legal Requirements
The concept identifies GDPR and consent as requirements, while PESTEL identifies property-brokerage regulation as relevant context.

**Missing:** a product-specific legal review covering data responsibilities, retention/deletion, profiling and co-buyers' ownership, liability and exit arrangements.

## 18. Open Issues
Confirm the launch audience and geography, validate willingness to buy with newly matched people, and agree on the matching rules and integration access. The survey covers general housing experiences; it does not establish demand for co-buying.

**Missing:** evidence of co-buyer demand, decision owners and acceptance criteria for the MVP.