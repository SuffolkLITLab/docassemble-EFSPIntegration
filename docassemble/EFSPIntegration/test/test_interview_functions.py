import unittest
from ..interview_logic import (
    make_filters,
    filter_codes,
    make_filter,
    ContainAny,
    CodeType,
)

filing_types = [
    ("29811", "Change"),
    ("28191", "Interpleader"),
    ("28957", "Letters"),
    ("28971", "Lien"),
    ("29865", "Demand"),
    ("29907", "Designation"),
    ("56514", "Withdrawal"),
    ("29175", "Position"),
    ("66511", "Motion to Modify"),
    ("29214", "Property Settlement"),
    ("66524", "Motion to Vacate"),
    ("123493", "Claim"),
    ("29373", "Sale"),
    ("29471", "Summary Judgment"),
    ("29643", "Acknowledgment"),
    ("29658", "Addendum"),
    ("143027", "Award"),
    ("143033", "Citation (Returned)"),
    ("142566", "Appearance (No Fee: fee exempted by rule/statute)"),
    (
        "181708",
        "Alias Citation/Garnishment/Wage Deduction ($1,000.01 to $5,000.00) (Issued)",
    ),
    ("183586", "Answer - ($2,500.01 to $10K)"),
    ("183587", "Answer - (Up to $2,500)"),
    ("183588", "Appearance - ($2,500.01 to $10K)"),
    ("183589", "Appearance - (Up to $2,500)"),
    ("183590", "Appearance (Limited Entry-Local Counsel) - ($2,500.01 to $10K)"),
    ("183591", "Appearance (Limited Entry-Local Counsel) - (Up to $2,500)"),
    ("183592", "Appearance (Limited Scope) - ($2,500.01 to $10K)"),
    ("183593", "Appearance (Limited Scope) - (Up to $2,500)"),
    ("183599", "Counter Petition/Complaint - ($2,500.01 to $10K)"),
    ("183601", "Counter Petition/Complaint - (Up to $2,500)"),
    ("183602", "Response - ($2,500.01 to $10K)"),
    ("183603", "Response - (Up to $2,500)"),
    ("183605", "Third Party Complaint/Defendant - ($2,500.01 to $10K)"),
    ("183607", "Third Party Complaint/Defendant - (Up to $2,500)"),
    ("183610", "Cross-Complaint - (Up to $2,500)"),
    ("183611", "Cross-Complaint - ($2,500.01 to $10K)"),
    ("183612", "Notice of Limited Scope Appearance - ($2,500.01 to $10K)"),
    ("183613", "Notice of Limited Scope Appearance - (Up to $2,500)"),
    ("143044", "Correspondence"),
    ("143045", "Data/Information Sheet"),
    ("143053", "Garnishment (Returned)"),
    ("143087", "Petition Vacate/Modify Final Order-Eviction (w/in 30 days) (no fee)"),
    (
        "143088",
        "Petition Vacate/Modify Final Order-Small Claim (w/in 30 days) (no fee)",
    ),
    ("143121", "Wage Deduction (Returned)"),
    ("143126", "Admission"),
    ("143127", "Affidavit"),
    ("143128", "Agreement"),
    ("143130", "Alias Summons (Issued)"),
    ("143131", "Alias Summons (Returned)"),
    ("143132", "Amended Complaint"),
    ("143133", "Amended Filing"),
    ("143134", "Amended Notice of Appeal"),
    ("143135", "Answer"),
    ("143139", "Appearance (No Fee: fee previously paid on behalf of party)"),
    ("143140", "Application"),
    ("143141", "Appointment"),
    ("143142", "Bond"),
    ("143143", "Brief"),
    ("143146", "Certificate"),
    ("143147", "Citation/Garnishment/Wage Deduction ($1,000.01 to $5,000.00) (Issued)"),
    ("143148", "Citation/Garnishment/Wage Deduction ($5,000.01 or more) (Issued)"),
    ("143149", "Citation/Garnishment/Wage Deduction (up to $1,000.00) (Issued)"),
    ("143151", "Consent"),
    ("143153", "Contempt of Court (Direct Civil)"),
    ("143154", "Contempt of Court (Direct Criminal)"),
    ("143155", "Contempt of Court (Indirect Civil)"),
    ("143156", "Contempt of Court (Indirect Criminal)"),
    ("143157", "Corrected Filing-Court Ordered"),
    ("143158", "Denial"),
    ("143159", "Deposition"),
    ("143160", "Detainer"),
    ("143161", "Discovery"),
    ("143162", "Dismissal"),
    ("143164", "Exhibit"),
    ("143165", "Hearing"),
    ("143166", "Interrogatories"),
    ("143167", "Inventory"),
    ("143168", "Judgment"),
    ("143169", "Jury Demand - 12 Person"),
    ("143170", "Jury Demand - 6 Person"),
    (
        "143171",
        "Jury Demand - 6 Person (12 Person Jury - where 6 person paid by other party)",
    ),
    ("143172", "Jury Instructions"),
    ("143173", "Leave"),
    ("143174", "List"),
    ("143175", "Mandate"),
    ("143176", "Memorandum"),
    ("143177", "Motion"),
    ("143178", "Motion for Redaction & Confidential Filing"),
    ("143179", "Notice"),
    ("143180", "Notice Confidential Info w/i Court Filing"),
    ("143181", "Notice of Appeal"),
    ("143182", "Notice of Hearing"),
    ("143183", "Notice of Motion"),
    ("143184", "Oath"),
    ("143185", "Objection"),
    ("143186", "Offer"),
    ("143187", "Order"),
    ("143188", "Other Document Not Listed"),
    ("143189", "Petition"),
    ("143190", "Petition for Rule to Show Cause"),
    ("143191", "Petition No Contact Order"),
    ("143192", "Petition No Stalking Order"),
    ("143193", "Petition Order of Protection"),
    ("143194", "Petition to Intervene"),
    ("143195", "Petition to Seal"),
    ("143196", "Petition Vacate/Modify Final Judgment/Order (> 30 days)"),
    ("143197", "Petition Vacate/Modify Final Judgment/Order (w/in 30 days)"),
    ("143198", "Petition Vacate/Modify Final Order-Enforce Support (no fee)"),
    ("143200", "Petition Vacate/Modify Final Order-Withholding Order (no fee)"),
    ("143202", "Proof of Service/Certificate of Service"),
    ("143203", "Proposal"),
    ("143204", "Proposed Order"),
    ("143205", "Quash"),
    ("143206", "Receipt"),
    ("143207", "Record Sheet"),
    ("143208", "Release"),
    ("143209", "Reply"),
    ("143210", "Report"),
    ("143211", "Report of Proceedings"),
    ("143212", "Request"),
    ("143213", "Request for Preparation of Record on Appeal"),
    ("143216", "Response (No Fee)"),
    ("143217", "Return"),
    ("143218", "Satisfaction/Release of Judgment"),
    ("143219", "Service"),
    ("143220", "Statement"),
    ("143221", "Stipulation"),
    ("143222", "Subpoena (Return)"),
    ("143223", "Subpoena (to Issue)"),
    ("143224", "Substitution"),
    ("143225", "Summons (Issued)"),
    ("143226", "Summons (Returned)"),
    ("143227", "Supplemental"),
    ("143228", "Terminate"),
    ("143229", "Transcript"),
    ("143230", "Transfer"),
    ("143231", "Verdict"),
    ("143232", "Verification"),
    ("143233", "Victim Counselor's Report"),
    ("143234", "Waiver"),
    ("143235", "Warrant (Returned)"),
    ("143236", "Worksheet"),
    (
        "181728",
        "Alias Citation/Garnishment/Wage Deduction ($5,000.01 or more) (Issued)",
    ),
    ("181748", "Alias Citation/Garnishment/Wage Deduction (up to $1,000.00) (Issued)"),
    ("181783", "Body Attachment (Issued)"),
    ("181800", "Body Attachment (Returned)"),
    ("181818", "Counter Petition/Complaint (no fee)"),
    ("181874", "Motion to Continue or Extend Time"),
    ("205658", "Identity Theft Affidavit"),
    ("181904", "Notice of Court Date for Motion"),
    ("181946", "Notice of Withdrawal Limited Scope Appearance"),
    ("181966", "Objection to Withdrawal Limited Scope Appearance"),
    ("248659", "Additional Proof of Delivery"),
    ("181996", "Petition to Intervene (Petitioner)"),
    ("248684", "Additional Paragraphs for Answer/Response"),
    ("248701", "Proof of Delivery"),
    ("182011", "Petition to Intervene (Respondent)"),
    ("251242", "Motion for New Trial"),
    ("182036", "Proof"),
    ("182060", "Report on Civil Judgment Involving Motor Vehicle Accident"),
    ("182081", "Request & Order for Interpreter"),
    ("292109", "Certified Inventory List"),
    ("274179", "Additional Defendants (Small Claims Complaint)"),
    ("274180", "Additional Reasons (Small Claims Complaint)"),
    ("274181", "Notice of Bankruptcy"),
    ("274182", "Notice of Interlocutory Appeal"),
    ("274183", "Order Appointing Special Process Server"),
    ("274184", "Small Claims Order"),
    ("206602", "Amended Information"),
    ("206604", "Bond Assignment"),
    ("206605", "Consolidate"),
    ("206606", "Contract"),
    ("206609", "Extended Media Coverage"),
    ("206610", "Final Judgment/Order"),
    ("206611", "Mistrial"),
    ("206613", "Motion to Vacate/Amend Final Order"),
    ("206614", "Other Document Not Listed (Confidential)"),
    ("206615", "Other Document Not Listed (Non-confidential)"),
    ("206616", "Proof"),
    ("206617", "Suppress"),
    ("206618", "Witness"),
    ("292149", "Change of Address"),
    ("292192", "Declaration"),
    ("292257", "Renunciation"),
    ("292281", "Reviewing Court Order"),
    ("292321", "Security for Costs"),
    ("292340", "Vouchers"),
]


class TestInterviews(unittest.TestCase):
    def test_no_exclude(self):
        filters = make_filters(["Appearance"])
        options, _ = filter_codes(filing_types, filters, None, None)

        self.assertEqual(12, len(options))

    def test_exclude(self):
        filters = make_filters(["Appearance"])
        exclude_filter = make_filter(
            ContainAny(["Limited Scope", "Limited Entry-Local Counsel", "No Fee"])
        )

        options, _ = filter_codes(filing_types, filters, None, exclude_filter)

        self.assertEqual(2, len(options))
        self.assertIn(("183588", "Appearance - ($2,500.01 to $10K)"), options)

    def test_code_filter(self):
        filters = make_filters([CodeType("143184")])
        options, _ = filter_codes(filing_types, filters, None, None)

        self.assertEqual(1, len(options))
        self.assertEqual(options[0][1], "Oath")

    def test_func_filter(self):
        filters = make_filters([lambda y: y[0] == "143184"])
        options, _ = filter_codes(filing_types, filters, None, None)

        self.assertEqual(1, len(options))
        self.assertEqual(options[0][1], "Oath")
