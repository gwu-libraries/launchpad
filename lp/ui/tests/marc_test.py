import os
import unittest

import pymarc

from ui.marc import extract


class MarcExtractTests(unittest.TestCase):

    def get_record(self, filename):
        path = os.path.join(os.path.dirname(__file__), "data", filename)
        if not os.path.isfile(path):
            return {}
        reader = pymarc.MARCReader(open(path))
        return reader.next()

    def test_source_description_588(self):
        r = self.get_record("588.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SOURCE_DESCRIPTION"], ['Latest issue consulted: Vol. 30 (2011).'])

    def test_description_300(self):
        r = self.get_record("300.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["DESCRIPTION"], ['xvi, 190 p. illus. 28 cm.'])

    def test_description_351(self):
        r = self.get_record("351.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["DESCRIPTION"][1], 'Organized into 3 series: I. Prison Materials, 1970-1972. II. CCNV. III. Personal/Family Materials.')
    
    def test_description_516(self):
        r = self.get_record("516.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["DESCRIPTION"], ['Text (electronic database).'])

    def test_description_344(self):
        r = self.get_record("344.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["DESCRIPTION"], ['1 videocassette (42 min.) : sound, color ; 1/2 in.', 'analog magnetic rda', 'VHS rda'])

    def test_description_345(self):
        pass

    def test_description_346(self):
        r = self.get_record("346.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["DESCRIPTION"], ['1 videocassette (42 min.) : sound, color ; 1/2 in.', 'analog magnetic rda', 'VHS rda'])

    def test_description_347(self):
        r = self.get_record("347.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["DESCRIPTION"], ['1 online resource (v, 65 leaves)', 'text file PDF rda.'])

    def test_production_credits_508(self):
        r = self.get_record("508.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["PRODUCTION_CREDITS"], ['Issued under the auspices of the Royal Institute of International Affairs.'])

    def test_series_440(self):
        r = self.get_record("440.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SERIES"], ['Religion and civilization series'])

    def test_series_800(self):
        r = self.get_record("800.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SERIES"], ['Melville, Herman, 1819-1891. Works. 1968 ; v. 2.'])

    def test_series_810(self):
        r = self.get_record("810.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SERIES"], ['United States. Congress. House. Report ; 90th Congress, no. 219.'])

    def test_series_811(self):
        r = self.get_record("811.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SERIES"], ['Drake Conference (1944 : Drake University). Drake lectures.'])

    def test_series_830(self):
        r = self.get_record("830.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SERIES"], ['Louisiana State University studies. Coastal studies series ; no. 10.'])

    def test_title_history_580(self):
        r = self.get_record("580.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["TITLE_HISTORY"], ['Continued as an online resource with the title AFI catalog.'])

    def test_citation_510(self):
        r = self.get_record("510.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["CITATION"], ['Wobbe, R.A.  Graham Greene, A53a'])

    def test_finding_aids_555(self):
        r = self.get_record("555.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["FINDING_AIDS"], ['Vols. 1 (1970)-20 (1989). 1 v.; v. 21 (1990)-38 (2009). 1 v.'])

    def test_earlier_title_247(self):
        r = self.get_record("247.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["EARLIER_TITLE"], ['[Oxford] regional economic atlases. 1954', 'Oxford regional atlases. 1959-'])

    def test_earlier_title_780(self):
        r = self.get_record("780.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["EARLIER_TITLE"], ['AFI catalog (DLC)  2002565442 (OCoLC)51098219'])

    def test_standard_title_240(self):
        r = self.get_record("240.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["STANDARD_TITLE"], ['Auf dem Weg zur vaterlosen Gesellschaft. English'])

    def test_funding_sponsors_536(self):
        r = self.get_record("536.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["FUNDING_SPONSORS"], ['District of Columbia contract 82-1289'])

    def test_copyright_542(self):
        r = self.get_record("542.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["COPYRIGHT"], ['130861, 342054 DCU'])

    def test_copyright_264(self):
        r = self.get_record("264.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["COPYRIGHT_DATE"], ['2013.'])

    def test_system_requirements_538(self):
        r = self.get_record("538.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SYSTEM_REQUIREMENTS"], ['System requirements for accompanying computer disc: IBM or compatible PC.'])

    def test_other_title_130(self):
        r = self.get_record("130.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_TITLE"], ['Pesikta rabbati. English.'])

    def test_other_title_242(self):
        r = self.get_record("242.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_TITLE"], ['Dictionary and handbook of animal husbandry'])

    def test_other_title_246(self):
        r = self.get_record("246.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_TITLE"], ['Analysis of sexual humor'])

    def test_other_title_730(self):
        r = self.get_record("730.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_TITLE"], ['Wisconsin law review.'])

    def test_other_title_740(self):
        r = self.get_record("740.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_TITLE"], ['Auf dem Weg vaterlosen Gesellschaft.'])

    def test_other_title_247(self):
        r = self.get_record("247.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_TITLE"], ['[Oxford] regional economic atlases. 1954', 'Oxford regional atlases. 1959-'])

    def test_original_version_534(self):
        r = self.get_record("534.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["ORIGINAL_VERSION"], ['Reprint. Originally published: 1902.'])

    def test_title_changed_to_785(self):
        r = self.get_record("785.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["TITLE_CHANGED_TO"], ['Conference on Magnetism and Magnetic Materials. Proceedings of the annual ... Conference on Magnetism and Magnetic Materials 1087-3848 (DLC)sn 96005438 (OCoLC)9100782'])

    def test_other_authors_700(self):
        r = self.get_record("700.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_AUTHORS"], ['Coleman, James M.', 'Gagliano, Sherwood M.'])

    def test_other_authors_710(self):
        r = self.get_record("710.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_AUTHORS"], ['Gilfillan, S. Colum, 1889-', 'United States. Congress. Joint Economic Committee.'])

    def test_other_authors_711(self):
        r = self.get_record("711.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_AUTHORS"], ['Geneva Conference (1954). Documents relating to the discussion of Korea and Indo-China at the Geneva Conference.', 'Geneva Conference (1954). Further documents relating to the discussion of Indo-China at the Geneva Conference.'])

    def test_performers_511(self):
        r = self.get_record("511.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["PERFORMERS"], ['Ernest J. Simmons, lecturer.'])

    def test_in_collection_773(self):
        r = self.get_record("773.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["IN_COLLECTION"], ['American Historical Association. Annual report of the American Historical Association. Washington. 25 cm. v. 2 [1897] (OCoLC)1150082'])

    def test_in_collection_545(self):
        r = self.get_record("545.mrc")
        bib_data = extract(r)
        self.assertEqual(['Mitch Snyder (1943-1990) was a radical Catholic, advocate for the rights of homeless people, and leader of the Community for Creative Non-Violence (CCNV) in Washington, D.C. CCNV began as an anti-war group and became an advocacy group for the homeless.'], bib_data["BIOGRAPHICAL NOTES"])

    def test_notes_500(self):
        r = self.get_record("500.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["NOTES"], ['"A Helen and Kurt Wolff book."', 'Translation of Auf dem Weg zur vaterlosen Gesellschaft.', 'Bibliographical references included in "Notes" (p. 313-322)'])

    def test_notes_501(self):
        r = self.get_record("501.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["NOTES"], ['With: Revolution in civil rights. 4th ed., June 1968.'])

    def test_notes_504(self):
        r = self.get_record("504.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["NOTES"], ['Bibliography: p. [183]-190.'])

    def test_notes_507(self):
        r = self.get_record("507.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["NOTES"], ['Scale 1:625,000.'])

    def test_notes_521(self):
        r = self.get_record("521.mrc")
        bib_data = extract(r)
        self.assertIn( 'MPAA rating: Not rated.', bib_data['NOTES'])

    def test_notes_530(self):
        r = self.get_record("530.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["NOTES"], ['Also issued online.'])

    def test_notes_546(self):
        r = self.get_record("546.mrc")
        bib_data = extract(r)
        # the note is also present in 500 so it appears twice
        self.assertEqual(bib_data["NOTES"], ['Text in Old Russian, foreword and notes in English.', 'Text in Old Russian, foreword and notes in English.'])

    def test_notes_547(self):
        r = self.get_record("547.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["NOTES"], ['Title varies: -1924/25, Report of the Executive Committee of the British Institute of International Affairs to the annual general meeting of the institute; 1925/26-1936/37, Report of the Council of the Royal Institute of International Affairs. Annual general meeting of the institute (slight variation); 1937/38-, Annual report of the council. Submitted to the annual general meeting.'])

    def test_notes_550(self):
        r = self.get_record("550.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["NOTES"], ['Conferences for 197 - sponsored by the American Institute of Physics, the Magnetics Group of the Institute of Electrical and Electronic Engineers, in co-operation with the Metallurgical Society of the American Institute of Mining Metallurgical and Petroleum Engineers, the Office of Naval Research, the American Society for Testing and Materials.'])

    def test_notes_586(self):
        r = self.get_record("586.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["NOTES"], ['Pulitzer Prize, Fiction, 1967.'])

    def test_notes_590(self):
        r = self.get_record("590.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["NOTES"], ["Library's copy autographed by the author."])

    def test_geographic_area_043(self):
        r = self.get_record("043.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["GEOGRAPHIC_AREA"], ['Europe', 'United States'])

    def test_other_standard_identifer_024(self):
        r = self.get_record("024.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["OTHER_STANDARD_IDENTIFIER"], ['10.1596/1813-9450-4394'])

    def test_terms_of_usage_540(self):
        r = self.get_record("540.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["TERMS_OF_USAGE"], ['Includes bibliographical references (p. 237-240) and index.'])

    def test_summary_520(self):
        r = self.get_record("520.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SUMMARY"], ['A young Indian recounts his struggle to free himself from the restrictions of his caste.'])

    def test_publisher_number_028(self):
        r = self.get_record("028.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["PUBLISHER_NUMBER"], ['HPS 699 Boosey & Hawkes', 'HL48002117 H. Leonard'])

    def test_subjects_650(self):
        r = self.get_record("650.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SUBJECTS"], ['Internet in public administration -- United States -- Periodicals.', 'Information policy -- United States -- Data processing -- Periodicals.', 'Electronic government information -- United States -- Periodicals.', 'United States. E-Government Act of 2002 -- Periodicals.'])

    def test_subjects_600(self):
        r = self.get_record("600.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SUBJECTS"], ['Mann, Thomas C. (Thomas Clifton), 1912-', 'United States. Dept. of State -- Officials and employees.', 'United States -- Foreign relations -- 1963-1969.'])

    def test_subjects_610(self):
        r = self.get_record("610.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SUBJECTS"], ['Mann, Thomas C. (Thomas Clifton), 1912-', 'United States. Dept. of State -- Officials and employees.', 'United States -- Foreign relations -- 1963-1969.'])

    def test_subjects_630(self):
        r = self.get_record("630.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SUBJECTS"], ['Franco-Russian Alliance.', 'France -- Foreign relations -- Soviet Union -- 1870-1940.', 'Russia -- Foreign relations -- France -- 1894-1917.'])

    def test_subjects_651(self):
        r = self.get_record("651.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SUBJECTS"], ['Mud lumps.', 'Sediments (Geology) -- Louisiana.', 'Mississippi River -- Delta.'] )

    def test_subjects_655(self):
        r = self.get_record("655.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["SUBJECTS"], ['World War, 1939-1945 -- Fiction.'])

    def test_contents_505(self):
        r = self.get_record("505.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["CONTENTS"], ['v. 1. Text.--v. 2. Plates.'])

    def test_contents_990(self):
        r = self.get_record("990.mrc")
        bib_data = extract(r)
        self.assertIn('Philosophy of religion and the question of God.', bib_data['CONTENTS'][0])

    def test_reproduction_533(self):
        r = self.get_record("533.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["REPRODUCTION"], ['Photocopy.'])

    def test_manufacture_numbers_028(self):
        r = self.get_record("028.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["MANUFACTURE_NUMBERS"], ['HPS 699 Boosey & Hawkes', 'HL48002117 H. Leonard'])

    def test_thesis_dissertation_502(self):
        r = self.get_record("502.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["THESIS_DISSERTATION"], ['Thesis (M.A.)--Cornell, 1964.'])

    def test_genre_655(self):
        r = self.get_record("655.mrc")
        bib_data = extract(r)
        self.assertEqual(bib_data["GENRE"], ["War stories."])
