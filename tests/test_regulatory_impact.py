from datetime import date
from mailo_cli.regulatory import ChangeType, RegulatoryChange, SourceLocator
from mailo_cli.regulatory.impact import ImpactLinkStatus, link_change_to_obligations
from mailo_cli.regulatory.obligations import Obligation, ObligationModality

def _change(locator):
    return RegulatoryChange(change_id="change-1",change_type=ChangeType.TEXT_CHANGED,source_id="eu-ai-act",old_version_id="old",new_version_id="new",effective_date=date(2026,7,27),amendment_source_id="amending-reg",amendment_locator=SourceLocator("Article 1",paragraph="13"),source_url="https://example.org/source",summary="Reviewed change.",old_locator=locator,new_locator=locator)

def _obligation(locator,source_id="eu-ai-act"):
    return Obligation(obligation_id="obl-1",source_id=source_id,locator=locator,actor="deployer",action="perform",object="assessment",modality=ObligationModality.MUST)

def test_exact_locator_creates_traceable_match_candidate():
    locator=SourceLocator("Article 27",paragraph="4")
    result=link_change_to_obligations(_change(locator),(_obligation(locator),))
    assert len(result)==1
    assert result[0].status is ImpactLinkStatus.LOCATOR_MATCH
    assert result[0].reviewed is False

def test_same_article_different_paragraph_requires_review():
    result=link_change_to_obligations(_change(SourceLocator("Article 27",paragraph="4")),(_obligation(SourceLocator("Article 27",paragraph="1")),))
    assert result[0].status is ImpactLinkStatus.REVIEW_REQUIRED

def test_different_source_or_article_is_not_linked():
    change=_change(SourceLocator("Article 27",paragraph="4"))
    obligations=(_obligation(SourceLocator("Article 28",paragraph="1")),_obligation(SourceLocator("Article 27",paragraph="4"),source_id="gdpr"))
    assert link_change_to_obligations(change,obligations)==()
