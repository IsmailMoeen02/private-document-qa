"""The dummy company documents. Harbourview Advisory is a made-up firm; every rule and number below is invented for this demo.
Each document: id, title, format (pdf, docx, txt), groups allowed to read it ("everyone" or named groups), and sections of (heading, [paragraphs])."""
DOCS = [
 {"id": "employee-handbook", "title": "Employee Handbook", "format": "docx", "groups": ["everyone"], "sections": [
  ("Working hours", ["Standard working hours are 9:00 to 17:30 with a 45 minute unpaid lunch break. Core hours, when everyone is expected to be available, are 10:00 to 16:00.",
                     "Overtime must be agreed with your manager in advance. Agreed overtime is taken as time off in lieu within three months."]),
  ("Annual leave", ["Full-time employees receive 22 working days of annual leave per year, plus the public holidays of England and Wales. The leave year runs from 1 January to 31 December.",
                    "Up to 5 unused days can be carried over into the next year and must be taken by 31 March. Leave requests are made in the people portal and need your manager's approval at least two weeks ahead for periods longer than five days."]),
  ("Sick leave", ["Employees receive 10 days of paid sick leave per year. Tell your manager before 10:00 on the first day of absence.",
                  "A doctor's note is required after 3 consecutive days of absence."]),
  ("Parental leave", ["Birth parents receive 14 weeks of paid parental leave. Partners receive 4 weeks of paid leave, which can be taken at any point in the first year."]),
  ("Remote work", ["You may work from home up to 2 days per week, agreed with your manager. Core hours still apply on remote days.",
                   "A one-off home office allowance of 400 is available once every 3 years for a desk, chair or monitor. Keep the receipt."]),
  ("Probation and notice", ["New employees serve a probation period of 3 months. After probation the notice period is 1 month for either side. During probation it is 1 week."])]},
 {"id": "it-security-policy", "title": "IT Security Policy", "format": "pdf", "groups": ["everyone"], "sections": [
  ("Passwords", ["Passwords must be at least 14 characters long. Use a passphrase or the company password manager. Passwords are changed only when a compromise is suspected, not on a fixed schedule.",
                 "Never share your password, even with IT staff. IT will never ask for it."]),
  ("Multi-factor authentication", ["Multi-factor authentication is mandatory for email, the VPN and the finance system. Use the authenticator app. SMS codes are not permitted."]),
  ("Devices", ["All laptops are encrypted. Screens lock automatically after 5 minutes of inactivity.",
               "Report a lost or stolen device to the security desk within 1 hour of noticing. Do not wait until the next working day."]),
  ("Removable media and software", ["USB storage devices are banned unless approved by IT in writing. Install software only from the IT portal; requests are answered within 2 working days."]),
  ("Phishing", ["Report suspicious emails with the Report Phishing button in the mail client. Do not forward them. Never click links in unexpected messages asking you to sign in."])]},
 {"id": "data-retention-policy", "title": "Data Retention Policy", "format": "pdf", "groups": ["everyone"], "sections": [
  ("Financial records", ["Invoices, receipts and other financial records are kept for 7 years from the end of the financial year they relate to."]),
  ("People records", ["Employment records are kept for 6 years after an employee leaves. Unsuccessful job applications are deleted after 6 months."]),
  ("Contracts", ["Customer and supplier contracts are kept for 6 years after the contract ends."]),
  ("Email, backups and cameras", ["Email is archived for 3 years and then deleted. System backups are kept for 90 days. CCTV footage is overwritten after 30 days unless it is needed for an incident."]),
  ("Deletion requests", ["A request from a person to delete their personal data is answered within 30 days. Send it to the data protection officer."])]},
 {"id": "travel-expense-policy", "title": "Travel and Expense Policy", "format": "docx", "groups": ["everyone"], "sections": [
  ("Approval and claims", ["Any single expense over 150 needs your manager's approval before you spend it. Claims must be submitted within 30 days of the expense, with a receipt for anything over 15.",
                           "Claims submitted after 30 days are paid only with finance director approval."]),
  ("Meals", ["The daily meal limit is 45 for domestic travel and 60 for international travel. Alcohol is not reimbursed."]),
  ("Flights and hotels", ["Book economy class for flights shorter than 6 hours. Premium economy is allowed for flights of 6 hours or longer.",
                          "The hotel limit is 140 per night in UK cities and 190 per night in London and international capitals."]),
  ("Car travel", ["Business mileage in your own car is reimbursed at 0.45 per mile. Parking and tolls are reimbursed with a receipt."])]},
 {"id": "procurement-policy", "title": "Procurement Policy", "format": "pdf", "groups": ["everyone"], "sections": [
  ("Quotes and tenders", ["Purchases up to 1,000 need one written quote. Purchases from 1,000 to 10,000 need three written quotes. Purchases above 10,000 need a formal tender and the finance director's sign-off."]),
  ("Preferred suppliers", ["The preferred supplier list is reviewed once a year in September. Use a preferred supplier when one exists for the category."]),
  ("Conflicts of interest", ["Declare any personal or family interest in a supplier to your manager before the purchase. The declaration is recorded in the supplier file."])]},
 {"id": "onboarding-guide", "title": "Onboarding Guide", "format": "txt", "groups": ["everyone"], "sections": [
  ("Your first day", ["Arrive at 9:30 and ask for the IT desk on the second floor to collect your laptop. Your manager will meet you at 10:00."]),
  ("Your buddy", ["Every new starter is paired with a buddy from another team for the first 3 months. Meet them in your first week."]),
  ("Training", ["Security awareness training must be completed within 7 days of starting. You will receive the link by email on day one."]),
  ("Pay", ["Salary is paid on the last working day of each month. The payroll cut-off for expenses and changes is the 20th of the month."])]},
 {"id": "office-safety", "title": "Office Safety Guide", "format": "pdf", "groups": ["everyone"], "sections": [
  ("Fire", ["The fire assembly point is car park B, behind the main entrance. Evacuation drills are held twice a year. Do not use the lifts during an alarm."]),
  ("First aid", ["First aiders wear a green lanyard. The first aid kits are at reception and on each floor kitchen."]),
  ("Incidents", ["Report any accident or near miss within 24 hours using the incident form on the intranet."]),
  ("Visitors", ["All visitors sign in at reception and wear a visitor badge. You are responsible for your guest at all times."])]},
 {"id": "customer-service-agreement", "title": "Customer Service Agreement Template", "format": "docx", "groups": ["legal", "finance"], "sections": [
  ("Payment", ["Invoices are payable within 30 days of the invoice date. Late payment carries interest at 4 percent above the Bank of England base rate."]),
  ("Liability", ["Our total liability under this agreement is limited to 100 percent of the fees paid in the 12 months before the claim arose."]),
  ("Termination", ["Either party may end this agreement with 60 days' written notice. Either party may end it immediately for material breach that is not fixed within 14 days of notice."]),
  ("Confidentiality and law", ["Confidentiality obligations continue for 5 years after the agreement ends. This agreement is governed by the law of England and Wales."])]},
 {"id": "nda-template", "title": "Mutual NDA Template", "format": "txt", "groups": ["legal"], "sections": [
  ("Term", ["The confidentiality obligations in this agreement last for 3 years from the date it is signed."]),
  ("Permitted disclosure", ["A party may disclose confidential information to its professional advisers and to staff who need it, if they are bound by equivalent duties."]),
  ("Return of documents", ["On written request, each party will return or destroy the other party's confidential documents within 14 days and confirm this in writing."])]},
 {"id": "salary-bands", "title": "Salary Bands and Reviews (HR only)", "format": "docx", "groups": ["hr"], "sections": [
  ("Bands", ["Band A is 28,000 to 36,000. Band B is 36,000 to 48,000. Band C is 48,000 to 65,000. Band D is 65,000 to 85,000. Directors are outside the bands."]),
  ("Reviews", ["Salary reviews take place every April. Changes take effect from 1 May."]),
  ("Bonus", ["The annual bonus pool is 6 percent of pre-tax profit. An individual bonus is capped at 10 percent of salary."])]},
 {"id": "disciplinary-procedure", "title": "Disciplinary Procedure (HR only)", "format": "pdf", "groups": ["hr"], "sections": [
  ("Stages", ["The stages are a verbal warning, a written warning, a final written warning and dismissal. Gross misconduct may skip stages."]),
  ("Investigation", ["An investigation must be completed within 15 working days of the allegation being raised."]),
  ("Appeals", ["An employee may appeal any outcome within 5 working days of receiving it. The appeal is heard by a manager who was not involved in the original decision."])]},
 {"id": "budget-2027", "title": "Budget 2027 (Finance only)", "format": "docx", "groups": ["finance"], "sections": [
  ("Spending limits", ["The marketing budget for 2027 is 180,000. The capital expenditure ceiling is 250,000."]),
  ("Hiring and travel", ["The hiring plan allows 9 new roles in 2027. The travel budget is cut by 8 percent compared with 2026."])]},
]
USERS = [  # username, display name, groups (everyone is implicit)
 ("ayesha", "Ayesha (staff)", []), ("omar", "Omar (HR)", ["hr"]), ("sara", "Sara (finance)", ["finance"]), ("imran", "Imran (legal)", ["legal"])]
