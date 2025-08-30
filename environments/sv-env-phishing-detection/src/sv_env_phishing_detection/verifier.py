"""PhishingDetectionVerifier implementation for email phishing detection."""

from __future__ import annotations

import re
from typing import Any, Mapping
from urllib.parse import urlparse

from .interfaces import Verifier as VerifierProtocol


class PhishingDetectionVerifier(VerifierProtocol):
    """Verifier for phishing email detection accuracy.

    This verifier analyzes email content for phishing indicators and evaluates
    the accuracy of phishing/legitimate classifications. It uses pattern matching,
    URL analysis, and content heuristics to identify phishing attempts.
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """Initialize the phishing detection verifier.

        Args:
            confidence_threshold: Minimum confidence score to classify as phishing
        """
        self.confidence_threshold = confidence_threshold
        self._last_details: dict[str, Any] = {}

        # Define phishing indicator patterns
        self.phishing_patterns = {
            "urgency": [
                r"urgent",
                r"immediate action",
                r"act now",
                r"expires? (today|soon|in \d+ hours?)",
                r"limited time",
                r"don't (miss|delay)",
                r"last chance",
                r"final (notice|warning|reminder)",
            ],
            "financial_lure": [
                r"congratulations.*won",
                r"claim your (prize|reward|money)",
                r"million dollars?",
                r"tax refund",
                r"unclaimed (funds?|money|property)",
                r"inheritance",
                r"lottery",
                r"free money",
                r"get rich",
            ],
            "credential_request": [
                r"verify your (account|identity|password)",
                r"confirm your",
                r"update your (information|details|account)",
                r"suspended account",
                r"click here to (verify|confirm|update)",
                r"validate your",
                r"re-?enter your password",
                r"security verification",
            ],
            "suspicious_sender": [
                r"no-?reply@",
                r"do-?not-?reply@",
                r"@[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}",  # IP addresses
                r"@.*\.(tk|ml|ga|cf)$",  # Suspicious TLDs
                r"[0-9]{5,}@",  # Many numbers in email
                r"amazon.*@(?!amazon\.com)",  # Impersonation
                r"paypal.*@(?!paypal\.com)",
                r"microsoft.*@(?!microsoft\.com)",
            ],
            "generic_greeting": [
                r"dear (customer|user|member|account holder|valued)",
                r"dear sir/madam",
                r"attention:",
                r"notice to:",
                r"hello there",
                r"greetings",
            ],
            "threat_language": [
                r"(account|service) will be (closed|suspended|terminated)",
                r"legal action",
                r"arrest",
                r"unauthorized (access|activity|transaction)",
                r"suspicious activity",
                r"security (breach|alert|warning)",
                r"fraudulent",
            ],
            "poor_grammar": [
                r"recieve",  # Common misspelling
                r"loose your",  # Should be "lose"
                r"there account",  # Should be "their"
                r"you're account",  # Should be "your"
                r"kindly\s+\w+",  # Overuse of "kindly"
                r"do the needful",
                r"revert back",
            ],
            "suspicious_links": [
                r"bit\.ly",
                r"tinyurl",
                r"goo\.gl",
                r"ow\.ly",
                r"short\.link",
                r"click\.here",
                r"[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}",  # IP addresses in URLs
            ]
        }

        # Legitimate email indicators
        self.legitimate_patterns = {
            "professional": [
                r"unsubscribe",
                r"privacy policy",
                r"terms of service",
                r"contact us",
                r"customer service",
                r"reference number",
                r"order #\d+",
                r"invoice #\d+",
            ],
            "personalized": [
                r"hi [A-Z][a-z]+",  # Actual name
                r"dear [A-Z][a-z]+",
                r"your recent (purchase|order|transaction)",
                r"based on your preferences",
                r"you recently",
            ],
            "verified_sender": [
                r"@.*\.(gov|edu|org)$",
                r"noreply@.*\.(com|net|org)$",
                r"@(gmail|yahoo|outlook|hotmail)\.com$",
            ]
        }

    def score(self, email_content: str, classification: str) -> float:
        """Score phishing detection accuracy.

        Args:
            email_content: The email text to analyze
            classification: The predicted classification ("phishing" or "legitimate")

        Returns:
            float: 1.0 for correct classification, 0.0 for incorrect
        """
        # Analyze email for phishing indicators
        phishing_score = self._calculate_phishing_score(email_content)

        # Determine actual classification based on analysis
        is_phishing = phishing_score >= self.confidence_threshold
        actual_classification = "phishing" if is_phishing else "legitimate"

        # Normalize classification input
        predicted = classification.lower().strip()
        if predicted in ["phish", "phishing", "malicious", "spam", "scam"]:
            predicted = "phishing"
        elif predicted in ["legit", "legitimate", "safe", "genuine", "benign"]:
            predicted = "legitimate"

        # Calculate accuracy
        is_correct = predicted == actual_classification

        # Store details
        self._last_details = {
            "email_content": email_content[:500] + "..." if len(email_content) > 500 else email_content,
            "predicted": predicted,
            "actual": actual_classification,
            "phishing_score": phishing_score,
            "is_correct": is_correct,
            "phishing_indicators": self._get_phishing_indicators(email_content),
            "legitimate_indicators": self._get_legitimate_indicators(email_content),
            "urls_found": self._extract_urls(email_content),
            "suspicious_url_count": len(self._find_suspicious_urls(email_content)),
        }

        return 1.0 if is_correct else 0.0

    def details(self) -> Mapping[str, Any]:
        """Return auxiliary information from the last verification.

        Returns:
            Mapping containing analysis details and indicators found
        """
        return self._last_details.copy()

    def _calculate_phishing_score(self, email_content: str) -> float:
        """Calculate overall phishing likelihood score.

        Args:
            email_content: Email text to analyze

        Returns:
            float: Phishing score between 0.0 and 1.0
        """
        # Count phishing indicators
        phishing_matches = 0
        phishing_categories = 0

        for category, patterns in self.phishing_patterns.items():
            category_matched = False
            for pattern in patterns:
                if re.search(pattern, email_content, re.IGNORECASE):
                    phishing_matches += 1
                    category_matched = True
            if category_matched:
                phishing_categories += 1

        # Count legitimate indicators
        legitimate_matches = 0
        legitimate_categories = 0

        for category, patterns in self.legitimate_patterns.items():
            category_matched = False
            for pattern in patterns:
                if re.search(pattern, email_content, re.IGNORECASE):
                    legitimate_matches += 1
                    category_matched = True
            if category_matched:
                legitimate_categories += 1

        # Check for suspicious URLs
        suspicious_urls = self._find_suspicious_urls(email_content)
        if suspicious_urls:
            phishing_matches += len(suspicious_urls) * 2  # Weight URLs heavily
            phishing_categories += 1

        # Calculate base score
        if phishing_matches + legitimate_matches == 0:
            return 0.3  # Neutral if no indicators

        phishing_weight = phishing_matches * (1 + phishing_categories * 0.1)
        legitimate_weight = legitimate_matches * (1 + legitimate_categories * 0.1)

        # Score calculation with bias toward phishing detection (better safe than sorry)
        total_weight = phishing_weight + legitimate_weight
        if total_weight > 0:
            score = (phishing_weight * 1.2) / (total_weight + 1)  # Slight bias toward detecting phishing
        else:
            score = 0.3

        # Additional checks that increase phishing score
        if self._has_deceptive_urls(email_content):
            score = min(1.0, score + 0.2)

        if self._has_multiple_urgency_indicators(email_content):
            score = min(1.0, score + 0.15)

        return min(1.0, max(0.0, score))

    def _get_phishing_indicators(self, email_content: str) -> list[str]:
        """Get list of phishing indicators found in email.

        Args:
            email_content: Email text to analyze

        Returns:
            List of found phishing indicators
        """
        indicators = []

        for category, patterns in self.phishing_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, email_content, re.IGNORECASE)
                for match in matches:
                    indicators.append(f"{category}: {match.group()}")

        # Add suspicious URLs
        suspicious_urls = self._find_suspicious_urls(email_content)
        for url in suspicious_urls:
            indicators.append(f"suspicious_url: {url}")

        return indicators[:10]  # Limit to top 10 for readability

    def _get_legitimate_indicators(self, email_content: str) -> list[str]:
        """Get list of legitimate indicators found in email.

        Args:
            email_content: Email text to analyze

        Returns:
            List of found legitimate indicators
        """
        indicators = []

        for category, patterns in self.legitimate_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, email_content, re.IGNORECASE)
                for match in matches:
                    indicators.append(f"{category}: {match.group()}")

        return indicators[:5]  # Limit to top 5

    def _extract_urls(self, email_content: str) -> list[str]:
        """Extract all URLs from email content.

        Args:
            email_content: Email text

        Returns:
            List of URLs found
        """
        # Simple URL regex pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, email_content, re.IGNORECASE)

        # Also look for hidden URLs in HTML
        html_url_pattern = r'href\s*=\s*["\']([^"\']+)["\']'
        html_urls = re.findall(html_url_pattern, email_content, re.IGNORECASE)

        all_urls = urls + html_urls
        return list(set(all_urls))  # Remove duplicates

    def _find_suspicious_urls(self, email_content: str) -> list[str]:
        """Find suspicious URLs in email content.

        Args:
            email_content: Email text

        Returns:
            List of suspicious URLs
        """
        suspicious = []
        urls = self._extract_urls(email_content)

        for url in urls:
            # Check for URL shorteners
            if any(shortener in url.lower() for shortener in ['bit.ly', 'tinyurl', 'goo.gl', 'ow.ly']):
                suspicious.append(url)
                continue

            # Check for IP addresses
            if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
                suspicious.append(url)
                continue

            # Check for suspicious domains
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()

                # Suspicious TLDs
                if any(domain.endswith(tld) for tld in ['.tk', '.ml', '.ga', '.cf']):
                    suspicious.append(url)

                # Look-alike domains (simple check)
                for brand in ['paypal', 'amazon', 'microsoft', 'google', 'apple', 'facebook']:
                    if brand in domain and not domain.endswith(f'{brand}.com'):
                        suspicious.append(url)
                        break
            except:
                pass

        return suspicious

    def _has_deceptive_urls(self, email_content: str) -> bool:
        """Check if email contains deceptive URL practices.

        Args:
            email_content: Email text

        Returns:
            bool: True if deceptive URLs found
        """
        # Check for URL vs display text mismatch in HTML
        html_link_pattern = r'<a[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>([^<]+)</a>'
        matches = re.finditer(html_link_pattern, email_content, re.IGNORECASE)

        for match in matches:
            url = match.group(1)
            display_text = match.group(2)

            # Check if display text looks like a URL but doesn't match href
            if re.match(r'https?://', display_text) and url != display_text:
                return True

            # Check if display text contains a brand name but URL doesn't
            for brand in ['paypal', 'amazon', 'microsoft', 'google']:
                if brand in display_text.lower() and brand not in url.lower():
                    return True

        return False

    def _has_multiple_urgency_indicators(self, email_content: str) -> bool:
        """Check if email has multiple urgency indicators.

        Args:
            email_content: Email text

        Returns:
            bool: True if multiple urgency indicators found
        """
        urgency_count = 0
        for pattern in self.phishing_patterns.get("urgency", []):
            if re.search(pattern, email_content, re.IGNORECASE):
                urgency_count += 1
                if urgency_count >= 3:
                    return True
        return False

    def classify(self, email_content: str) -> str:
        """Classify an email as phishing or legitimate.

        Args:
            email_content: The email text to classify

        Returns:
            str: "phishing" or "legitimate"
        """
        score = self._calculate_phishing_score(email_content)
        return "phishing" if score >= self.confidence_threshold else "legitimate"
