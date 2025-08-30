"""PhishingDetectionEnvironment implementation for phishing email detection."""

from __future__ import annotations

import logging
from typing import Any, Mapping

import verifiers as vf
from datasets import Dataset

from .verifier import PhishingDetectionVerifier

logger = logging.getLogger(__name__)


class PhishingDetectionEnvironment:
    """SingleTurnEnv environment for phishing email detection.

    This environment implements PRD Environment #4: A SingleTurnEnv where models
    classify emails as phishing attempts or legitimate emails. The environment
    provides email text as prompts and expects classification labels as outputs.
    """

    def __init__(
        self,
        verifier: PhishingDetectionVerifier | None = None,
        max_examples: int = 1000,
        system_prompt: str | None = None,
    ):
        """Initialize the phishing detection environment.

        Args:
            verifier: Custom verifier instance (uses default if None)
            max_examples: Maximum number of examples to use from dataset
            system_prompt: Custom system prompt (uses default if None)
        """
        self.verifier = verifier or PhishingDetectionVerifier()
        self.max_examples = max_examples

        self.system_prompt = system_prompt or (
            "You are an email security analyst. Analyze the provided email and "
            "classify it as either 'Phishing' or 'Legitimate'. Consider factors "
            "like sender credibility, urgency tactics, suspicious links, requests "
            "for personal information, and grammatical errors. Respond with only "
            "the classification label."
        )

        self._dataset: Dataset | None = None
        self._env: vf.SingleTurnEnv | None = None

    def evaluate(self, email_content: str, model_output: str) -> tuple[float, Mapping[str, Any]]:
        """Evaluate a model's classification of an email.

        Args:
            email_content: The email text that was classified
            model_output: The model's classification response

        Returns:
            tuple: (reward, info) where reward is the RL signal and info contains
                   auxiliary data about the evaluation
        """
        # Extract classification from model output
        predicted_label = self._extract_classification(model_output)

        # Score the prediction
        reward = self.verifier.score(email_content, predicted_label)
        info = {
            **self.verifier.details(),
            "predicted_label": predicted_label,
            "model_output": model_output,
        }

        return reward, info

    def get_dataset(self) -> Dataset:
        """Get the dataset of emails for training/evaluation.

        Returns:
            Dataset containing emails with ground truth labels
        """
        if self._dataset is None:
            logger.info("Creating synthetic phishing detection dataset")
            self._dataset = self._create_synthetic_dataset()

        return self._dataset

    def get_verifiers_env(self) -> vf.SingleTurnEnv:
        """Get the underlying Verifiers SingleTurnEnv for RL training.

        Returns:
            vf.SingleTurnEnv: Configured environment ready for RL training
        """
        if self._env is None:
            self._env = self._create_verifiers_env()
        return self._env

    def _create_verifiers_env(self) -> vf.SingleTurnEnv:
        """Create the underlying Verifiers SingleTurnEnv."""
        dataset = self.get_dataset()

        def reward_classification_match(
            prompt: str, completion: str, answer: str, **kwargs
        ) -> float:
            """Reward function for exact classification match."""
            predicted = self._extract_classification(completion)
            actual = answer.strip().lower()
            return 1.0 if predicted.lower() == actual else 0.0

        rubric = vf.Rubric(
            funcs=[reward_classification_match],
            weights=[1.0],
        )

        return vf.SingleTurnEnv(
            dataset=dataset,
            rubric=rubric,
            system_prompt=self.system_prompt,
        )

    def _create_synthetic_dataset(self) -> Dataset:
        """Create a synthetic dataset for testing purposes."""
        examples = [
            # Phishing examples
            {
                "prompt": """Subject: Urgent: Your Account Will Be Suspended!

Dear Customer,

We have detected unusual activity on your account. Your account will be SUSPENDED within 24 hours unless you verify your identity immediately.

Click here to verify your account: http://bit.ly/verify-account-now

Please provide:
- Username
- Password
- Social Security Number

Act NOW to avoid losing access to your funds!

Best regards,
Account Security Team
no-reply@secure-bank-verify.tk""",
                "answer": "Phishing"
            },
            {
                "prompt": """Subject: Congratulations! You've Won $1,000,000!!!

Greetings,

You are the lucky winner of our international lottery! You've won ONE MILLION DOLLARS!

To claim your prize, please send us:
1. Your full name
2. Bank account details
3. Copy of your passport
4. Processing fee of $500

Send details to: lottery.winner.2024@gmail.com

Don't delay - you have only 48 hours to claim your prize!

International Lottery Commission""",
                "answer": "Phishing"
            },
            {
                "prompt": """Subject: Amazon Security Alert - Unauthorized Access

Dear User,

Someone tried to access your Amazon account from an unknown device.

Location: Russia
Device: Unknown

If this wasn't you, secure your account immediately:
https://amaz0n-security.weebly.com/verify

Enter your login credentials to secure your account.

Amazon Security
do-not-reply@amaz0n-alerts.com""",
                "answer": "Phishing"
            },
            {
                "prompt": """Subject: IRS Tax Refund - Action Required

Attention Taxpayer,

Our records show you are eligible for a tax refund of $3,458.23.

However, we need to verify your identity before processing.

Click here to submit your information:
www.irs-gov-refunds.ml/claim

Required information:
- Social Security Number
- Bank routing number
- Account number

Failure to respond within 72 hours will result in forfeiture of your refund.

Internal Revenue Service
refunds@irs-gov.ml""",
                "answer": "Phishing"
            },
            {
                "prompt": """Subject: PayPal: Your Account Has Been Limited

Dear PayPal User,

We've limited your account due to suspicious activity. To restore full access, you must verify your identity.

Click here to unlock your account:
http://tinyurl.com/paypal-unlock-2024

You will need to provide:
- Email and password
- Credit card information
- Security questions

Act quickly to avoid permanent suspension.

PayPal Security Team
security@paypaI.com (notice the capital I)""",
                "answer": "Phishing"
            },
            # Legitimate examples
            {
                "prompt": """Subject: Your Amazon Order Has Shipped

Hi John Smith,

Good news! Your order #123-4567890-1234567 has shipped.

Track your package:
https://www.amazon.com/gp/css/shiptrack/view.html?orderID=123-4567890-1234567

Items in this shipment:
- Echo Dot (4th Gen) - Smart speaker with Alexa
- Quantity: 1
- Total: $49.99

Delivery estimate: Thursday, December 14

Thanks for shopping with us!

Amazon.com
customer-service@amazon.com

To unsubscribe from shipping notifications, update your preferences in Your Account.""",
                "answer": "Legitimate"
            },
            {
                "prompt": """Subject: Your GitHub Security Code

Hey there!

A sign in attempt requires further verification because we did not recognize your device. To complete the sign in, enter the verification code on the unrecognized device.

Device: Chrome on Windows
Verification code: 123456

If you did not attempt to sign in to your account, your password may be compromised. Visit https://github.com/settings/security to create a new, strong password for your GitHub account.

If you'd like to automatically verify devices in the future, consider enabling two-factor authentication on your account. Visit https://help.github.com/articles/configuring-two-factor-authentication to learn more about keeping your account secure.

Thanks,
The GitHub Team""",
                "answer": "Legitimate"
            },
            {
                "prompt": """Subject: Your Monthly LinkedIn Network Update

Hi Sarah Johnson,

You have 3 new profile views this week!

People are noticing you on LinkedIn. See who viewed your profile:
https://www.linkedin.com/me/profile-views

Your network updates:
- 12 new connections in your network
- 45 new jobs in Software Engineering
- 8 people in your network changed positions

Stay connected,
The LinkedIn Team

You are receiving notification emails. Unsubscribe:
https://www.linkedin.com/e/v2/unsubscribe""",
                "answer": "Legitimate"
            },
            {
                "prompt": """Subject: Receipt for Your Spotify Premium Payment

Hi Michael Chen,

Thanks for your payment! Your Spotify Premium subscription has been renewed.

Payment details:
- Amount: $9.99 USD
- Payment method: Visa ending in 4567
- Billing period: Dec 10, 2024 - Jan 10, 2025
- Invoice #: SP-2024-12-1234567

Manage your subscription:
https://www.spotify.com/account/subscription/

Questions? Visit our support center:
https://support.spotify.com/

Rock on!
The Spotify Team

Spotify USA Inc.
support@spotify.com""",
                "answer": "Legitimate"
            },
            {
                "prompt": """Subject: Your Dropbox Storage Is Almost Full

Hi Alex Williams,

You're using 98% of your Dropbox Basic storage (1.96 GB of 2 GB).

When you run out of space, syncing will stop and you won't be able to add new files.

Upgrade to Dropbox Plus for 2 TB of storage:
https://www.dropbox.com/upgrade

Or free up space by deleting files:
https://www.dropbox.com/home

Need help? Visit our help center:
https://help.dropbox.com/

Happy Dropboxing!
The Dropbox Team

You're receiving this because you're signed up for Dropbox notifications. Change your preferences:
https://www.dropbox.com/account/notifications""",
                "answer": "Legitimate"
            },
            {
                "prompt": """Subject: Microsoft 365: Your Subscription Will Renew Soon

Hello Emma Davis,

This is a reminder that your Microsoft 365 Family subscription will automatically renew on December 25, 2024.

Subscription details:
- Product: Microsoft 365 Family
- Price: $99.99/year
- Payment method: MasterCard ending in 8901
- Next charge date: December 25, 2024

Manage your subscription:
https://account.microsoft.com/services

What's included:
- Premium Office apps
- 1 TB OneDrive cloud storage per person
- Advanced security features

Thank you for being a Microsoft 365 subscriber.

Microsoft Corporation
microsoft@email.microsoft.com

Privacy Statement: https://privacy.microsoft.com""",
                "answer": "Legitimate"
            },
            # More nuanced examples
            {
                "prompt": """Subject: Re: Your Recent Support Ticket

Dear Valued Customer,

Thank you for contacting us. We need to verify your account to process your support request #789456.

For security purposes, please confirm your identity by clicking below:
http://support-verification.000webhostapp.com/verify?ticket=789456

This link will expire in 24 hours.

Best regards,
Customer Support Team
support@customer-help.site""",
                "answer": "Phishing"
            },
            {
                "prompt": """Subject: University IT: Password Expiration Notice

Dear Student,

Your university email password will expire in 7 days. To avoid interruption of service, please update your password.

Click here to update: http://university-it-portal.weebly.com/password-reset

Requirements:
- Minimum 8 characters
- Include numbers and special characters

IT Help Desk
it-support@university-mail.net""",
                "answer": "Phishing"
            },
            {
                "prompt": """Subject: Wells Fargo: Scheduled System Maintenance

Dear Robert Thompson,

We will be performing scheduled maintenance on our online banking system this weekend.

Maintenance window:
Saturday, Dec 16, 2024, 2:00 AM - 6:00 AM PST

During this time:
- Online banking may be temporarily unavailable
- Mobile app access may be limited
- ATMs and debit cards will work normally

No action is required on your part. We apologize for any inconvenience.

For 24/7 support, call: 1-800-869-3557

Wells Fargo Bank
onlinebanking@wellsfargo.com

View in browser: https://www.wellsfargo.com/email/maintenance-notice""",
                "answer": "Legitimate"
            },
            {
                "prompt": """Subject: Zoom: Your Cloud Recording Is Ready

Hi Jennifer Martinez,

Your cloud recording is now available:

Meeting topic: Q4 Planning Session
Date: December 10, 2024
Duration: 1 hr 15 min

View recording: https://zoom.us/rec/share/abc123def456ghi789
Passcode: Planning2024!

This recording will be available for 30 days. Download it to keep it longer.

Recording settings can be managed in your Zoom web portal:
https://zoom.us/profile/recording

Thanks for using Zoom!

notification@zoom.us
Don't want these emails? Update your notification settings:
https://zoom.us/profile/setting""",
                "answer": "Legitimate"
            }
        ]

        logger.info(f"Created synthetic dataset with {len(examples)} examples")
        return Dataset.from_list(examples)

    def _extract_classification(self, model_output: str) -> str:
        """Extract classification label from potentially verbose model output.

        Args:
            model_output: The model's raw output text

        Returns:
            str: Extracted classification ("Phishing" or "Legitimate")
        """
        output_lower = model_output.lower().strip()

        # Look for explicit labels first
        if "phishing" in output_lower or "phish" in output_lower:
            return "Phishing"
        elif "legitimate" in output_lower or "legit" in output_lower:
            return "Legitimate"

        # Look for other indicators of phishing
        phishing_indicators = ["scam", "fraudulent", "malicious", "suspicious", "fake", "spam"]
        if any(indicator in output_lower for indicator in phishing_indicators):
            return "Phishing"

        # Look for indicators of legitimate email
        legitimate_indicators = ["genuine", "authentic", "valid", "real", "safe", "benign"]
        if any(indicator in output_lower for indicator in legitimate_indicators):
            return "Legitimate"

        # Check for yes/no style answers to "Is this phishing?"
        if output_lower in ["yes", "yes.", "true"]:
            return "Phishing"
        elif output_lower in ["no", "no.", "false"]:
            return "Legitimate"

        # Fallback: return the first word if it matches expected labels
        words = output_lower.split()
        if words:
            first_word = words[0].rstrip('.,!?')
            if first_word in ["phishing", "phish"]:
                return "Phishing"
            elif first_word in ["legitimate", "legit"]:
                return "Legitimate"

        # Default fallback - assume legitimate (safer to not flag legitimate emails)
        return "Legitimate"
