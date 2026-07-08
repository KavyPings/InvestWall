"""Curated bank of real/representative scam keywords and phrases, specific
to Indian securities-market fraud. Serves two purposes:

1. Source material for expanding RISKY_KEYWORDS / rule patterns in
   phishing_rules.py (this file's SCAM_QUOTE_BANK is folded in below).
2. Few-shot grounding seeds for ml/scripts/generate_synthetic.py, so
   LLM-generated synthetic examples stay anchored to real scam phrasing
   instead of drifting into generic, unrealistic text.

Entries are paraphrased patterns grounded in public advisories and reporting
(SEBI investor-alert pages, SEBI press releases, RBI cautions, BSE/NSE
investor advisories, and cybercrime.gov.in/I4C fraud advisories) — not
verbatim scam messages. Each entry's `note` cites the general source
category so provenance stays traceable. Sources consulted:
- https://investor.sebi.gov.in/spot-any-scam.html
- https://www.sebi.gov.in/media-and-notifications/press-releases/may-2025/caution-to-investors-on-stock-market-scams-through-social-media-platforms_94064.html
- https://www.rbi.org.in/commonman/english/scripts/rbicautions.aspx
- BSE investor alerts re: deepfake CEO video impersonation (2025-2026)
- NSE investor advisory against "dabba" trading
- cybercrime.gov.in / I4C advisories on task-based investment fraud and
  digital-arrest scams (2025-2026)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScamQuote:
    text: str
    archetype: str
    note: str


SCAM_QUOTE_BANK: list[ScamQuote] = [
    # --- guaranteed_returns ---
    ScamQuote(
        "Guaranteed 40% returns every month, absolutely risk-free investment.",
        "guaranteed_returns",
        "SEBI investor-alert language: guaranteed/assured returns ignoring market risk.",
    ),
    ScamQuote(
        "Join our exclusive trading circle for consistent, no-loss weekly payouts.",
        "guaranteed_returns",
        "Paraphrase avoiding literal 'guaranteed returns' wording.",
    ),
    ScamQuote(
        "This is risk-free money for you, act before slots close tonight.",
        "guaranteed_returns",
        "Risk-free framing + urgency, matching SEBI's 'push you to make an immediate decision' red flag.",
    ),
    ScamQuote(
        "We offer near-certain returns that stay high regardless of how the market moves.",
        "guaranteed_returns",
        "SEBI spot-any-scam.html: 'remarkably high returns regardless of market conditions'.",
    ),
    # --- guaranteed_returns_daily_payout ---
    ScamQuote(
        "Get quick daily returns credited to your account, no waiting for month-end.",
        "guaranteed_returns_daily_payout",
        "SEBI spot-any-scam.html: 'quick daily returns' as a scam red flag.",
    ),
    ScamQuote(
        "Deposit today and start receiving fixed daily payouts from tomorrow onward.",
        "guaranteed_returns_daily_payout",
        "Daily-payout guaranteed-income pattern.",
    ),
    ScamQuote(
        "Double your capital in 15 days with our proven daily-compounding strategy.",
        "guaranteed_returns_daily_payout",
        "Multiply-your-money variant with compounding framing.",
    ),
    ScamQuote(
        "Our members withdraw profits every single day without fail, join now.",
        "guaranteed_returns_daily_payout",
        "Daily-withdrawal-profit claim pattern.",
    ),
    # --- unregistered_advisor_paid_tips ---
    ScamQuote(
        "Pay a one-time fee to join my private tip service and get my personal stock picks daily.",
        "unregistered_advisor_paid_tips",
        "SEBI action pattern (Yash Trading Academy-type cases): unregistered advisor charging for stock tips.",
    ),
    ScamQuote(
        "I'm not SEBI-registered but I've helped thousands multiply their money, DM to subscribe.",
        "unregistered_advisor_paid_tips",
        "Unregistered-advisor self-disclosure pattern still selling paid signals.",
    ),
    ScamQuote(
        "Subscribe to my premium calls channel, verified 90% accuracy over the last year.",
        "unregistered_advisor_paid_tips",
        "Paid signal-service accuracy claim without SEBI registration.",
    ),
    ScamQuote(
        "Get lifetime access to my trading formula for a small one-time payment, results guaranteed.",
        "unregistered_advisor_paid_tips",
        "Lifetime-access paid-formula pattern.",
    ),
    # --- account_handling_scam ---
    ScamQuote(
        "Give me trading access to your account and I'll guarantee you a fixed monthly profit share.",
        "account_handling_scam",
        "SEBI alert: 'account handling' scams where fraudsters manage a victim's trading account.",
    ),
    ScamQuote(
        "Hand over your login and let our expert team trade on your behalf for assured profits.",
        "account_handling_scam",
        "Account-handling / portfolio-management scam pattern.",
    ),
    ScamQuote(
        "Our dealers will place trades directly in your demat account and split the guaranteed gains with you.",
        "account_handling_scam",
        "Account-handling scam variant with profit-sharing framing.",
    ),
    ScamQuote(
        "Just share your trading password, our algorithm handles everything and profit is assured.",
        "account_handling_scam",
        "Credential-sharing framed as convenience within an account-handling scam.",
    ),
    # --- complex_strategy_obfuscation ---
    ScamQuote(
        "Our proprietary highly complex investing technique is too advanced to explain simply, just trust the results.",
        "complex_strategy_obfuscation",
        "SEBI spot-any-scam.html: credits success to a 'highly complex investing technique' while withholding risk explanation.",
    ),
    ScamQuote(
        "It uses an advanced quant algorithm nobody else has access to, that's why returns are so consistent.",
        "complex_strategy_obfuscation",
        "Obfuscated-strategy justification for consistent returns.",
    ),
    ScamQuote(
        "The strategy is proprietary and confidential, but the track record speaks for itself.",
        "complex_strategy_obfuscation",
        "Refusal to explain mechanics while claiming a track record.",
    ),
    ScamQuote(
        "It's a complex hedge structure that eliminates downside, most people wouldn't understand it anyway.",
        "complex_strategy_obfuscation",
        "Complexity used to discourage due diligence.",
    ),
    # --- insider_tip ---
    ScamQuote(
        "Our insider tip has hit target 9 out of 10 times this month.",
        "insider_tip",
        "Sure-shot/insider stock-tip pattern.",
    ),
    ScamQuote(
        "I have insider information on tomorrow's announcement, buy before the news breaks.",
        "insider_tip",
        "Claimed inside information ahead of a market-moving announcement.",
    ),
    ScamQuote(
        "This sure-shot call is coming straight from someone inside the company.",
        "insider_tip",
        "Sure-shot framing citing an internal source.",
    ),
    ScamQuote(
        "Our research desk has called 9 out of 10 winning trades this month, join before we close registrations.",
        "insider_tip",
        "High win-rate claim combined with scarcity/urgency.",
    ),
    # --- fake_regulator_approval ---
    ScamQuote(
        "SEBI has approved this scheme, your capital is 100% safe.",
        "fake_regulator_approval",
        "False regulator-approval claim.",
    ),
    ScamQuote(
        "Congratulations, you've been selected for a government-backed wealth scheme.",
        "fake_regulator_approval",
        "Fake selection/eligibility framing implying official backing.",
    ),
    ScamQuote(
        "This investment plan is fully compliant with market regulator norms and RBI guidelines.",
        "fake_regulator_approval",
        "False compliance claim citing SEBI/RBI norms.",
    ),
    ScamQuote(
        "Our scheme has clearance from the exchange and the regulator, so there is zero risk to you.",
        "fake_regulator_approval",
        "False regulatory clearance claim used to imply zero risk.",
    ),
    # --- fake_sebi_registration_number ---
    ScamQuote(
        "Our SEBI registration number INA000012345 confirms we are fully authorised to manage your funds.",
        "fake_sebi_registration_number",
        "Fabricated/misused SEBI registration number cited to appear legitimate.",
    ),
    ScamQuote(
        "You can verify our SEBI licence number on our website, we are 100% government-registered.",
        "fake_sebi_registration_number",
        "Claims verifiable registration while directing away from SEBI's own intermediary-search tool.",
    ),
    ScamQuote(
        "As a SEBI-registered research analyst (reg. no. attached), I guarantee this stock will double.",
        "fake_sebi_registration_number",
        "Registration claim paired with an illegal guaranteed-return promise.",
    ),
    ScamQuote(
        "Check our certificate, we hold a valid SEBI registration for portfolio management services.",
        "fake_sebi_registration_number",
        "Fabricated PMS registration claim.",
    ),
    # --- impersonating_registered_entity ---
    ScamQuote(
        "This is an official update from your broker's research desk with an exclusive stock recommendation.",
        "impersonating_registered_entity",
        "SEBI PR 27/2025: fraudulent platforms impersonating SEBI-registered entities.",
    ),
    ScamQuote(
        "We are the official investment advisory arm of a leading NSE-listed brokerage.",
        "impersonating_registered_entity",
        "False affiliation with a real, recognisable brokerage name.",
    ),
    ScamQuote(
        "This message comes from the verified partner desk of a top registered financial firm.",
        "impersonating_registered_entity",
        "Impersonation of a reputable financial firm's partner/desk.",
    ),
    ScamQuote(
        "Our platform is powered by the same team behind a well-known SEBI-registered brokerage.",
        "impersonating_registered_entity",
        "Vague affiliation claim borrowing a known brokerage's credibility.",
    ),
    # --- sebi_vs_scam_countercampaign_spoof ---
    ScamQuote(
        "As part of SEBI's investor verification drive, please confirm your trading credentials here.",
        "sebi_vs_scam_countercampaign_spoof",
        "Spoofs SEBI's own 'SEBI vs SCAM' investor-awareness campaign to add false legitimacy.",
    ),
    ScamQuote(
        "This is your official SEBI investor-protection verification, complete it to avoid account suspension.",
        "sebi_vs_scam_countercampaign_spoof",
        "False claim of being an official SEBI verification step.",
    ),
    ScamQuote(
        "SEBI has flagged your account for a routine security check, click below to clear it.",
        "sebi_vs_scam_countercampaign_spoof",
        "Fake SEBI security-check notice used as a phishing hook.",
    ),
    ScamQuote(
        "Under the new SEBI investor safety initiative, all traders must re-verify their demat login today.",
        "sebi_vs_scam_countercampaign_spoof",
        "False regulatory-initiative framing to justify urgent credential re-entry.",
    ),
    # --- deepfake_ceo_endorsement ---
    ScamQuote(
        "In this video, our exchange's CEO personally reveals the stocks that will make you a multi-millionaire.",
        "deepfake_ceo_endorsement",
        "BSE investor alert pattern (deepfake CEO video, 2025-2026): fabricated CEO endorsement videos.",
    ),
    ScamQuote(
        "Watch how the MD explains this one stock that could turn ₹1 lakh into ₹80 lakh by 2027.",
        "deepfake_ceo_endorsement",
        "Deepfake-video pattern citing a specific future rupee target.",
    ),
    ScamQuote(
        "The company chairman confirms in this exclusive clip that this trading app is officially endorsed.",
        "deepfake_ceo_endorsement",
        "Fabricated executive endorsement of a trading app.",
    ),
    ScamQuote(
        "See the video where our founder reveals super-normal profits are guaranteed with this method.",
        "deepfake_ceo_endorsement",
        "'Extraordinary/super-normal profits' language from BSE deepfake-video advisories.",
    ),
    # --- deepfake_market_expert ---
    ScamQuote(
        "This well-known market analyst reveals his top 3 picks in this leaked video, don't miss it.",
        "deepfake_market_expert",
        "Fabricated video of a recognisable market expert giving stock picks they never made.",
    ),
    ScamQuote(
        "Listen to this exclusive audio where a famous fund manager tips this stock before it explodes.",
        "deepfake_market_expert",
        "Fabricated audio impersonation of a known fund manager/analyst.",
    ),
    ScamQuote(
        "In this interview clip, the expert says this is the only stock you need to buy this year.",
        "deepfake_market_expert",
        "Manipulated-media clip attributing a stock pick to a known expert.",
    ),
    ScamQuote(
        "Watch this rare video where the veteran investor personally recommends joining our platform.",
        "deepfake_market_expert",
        "Fabricated personal recommendation attributed to a known investor.",
    ),
    # --- fake_news_screenshot ---
    ScamQuote(
        "See this news article confirming the scheme was approved and covered by a leading financial channel.",
        "fake_news_screenshot",
        "Doctored/fabricated news-article screenshot claiming media or regulator endorsement.",
    ),
    ScamQuote(
        "This screenshot from a top business newspaper proves our platform is government-recognised.",
        "fake_news_screenshot",
        "Fake newspaper screenshot used as fabricated proof of legitimacy.",
    ),
    ScamQuote(
        "Forwarding the news clip where this stock was named the top pick by a national financial daily.",
        "fake_news_screenshot",
        "Fabricated financial-news endorsement forwarded as proof.",
    ),
    ScamQuote(
        "Attached is the official press coverage confirming SEBI cleared this investment plan.",
        "fake_news_screenshot",
        "Fake press-coverage attachment claiming SEBI clearance.",
    ),
    # --- telegram_recruit ---
    ScamQuote(
        "Limited seats left in our VIP Telegram tips group, first month free.",
        "telegram_recruit",
        "SEBI PR 27/2025: 'VIP Groups' recruitment pattern with false scarcity.",
    ),
    ScamQuote(
        "Join our exclusive WhatsApp trading community before registrations close tonight.",
        "telegram_recruit",
        "WhatsApp-group recruitment with urgency/scarcity.",
    ),
    ScamQuote(
        "Our private Telegram channel shares live buy/sell calls, request access now.",
        "telegram_recruit",
        "Live-calls channel recruitment pattern.",
    ),
    ScamQuote(
        "Only 20 spots open in today's tips group, once full we won't add anyone else.",
        "telegram_recruit",
        "Artificial capacity-limit scarcity tactic for group recruitment.",
    ),
    # --- vip_group_free_trial ---
    ScamQuote(
        "Try our VIP signals group free for 7 days, then continue for a small monthly fee.",
        "vip_group_free_trial",
        "Free-trial-to-paid-upsell pattern for tips groups.",
    ),
    ScamQuote(
        "First week is on the house, see our accuracy yourself before you pay anything.",
        "vip_group_free_trial",
        "Trial-period trust-building before monetisation.",
    ),
    ScamQuote(
        "Enjoy free access this week only, from next week the VIP group becomes paid-only.",
        "vip_group_free_trial",
        "Time-boxed free-trial urgency pattern.",
    ),
    ScamQuote(
        "No cost to join right now, but paid members get the earlier, more accurate calls.",
        "vip_group_free_trial",
        "Free-tier vs. paid-tier differentiation to pressure upgrade.",
    ),
    # --- social_media_guru_dm ---
    ScamQuote(
        "Hi, I saw your comment on that trading post, I personally mentor a few people to grow their portfolio.",
        "social_media_guru_dm",
        "cybercrime.gov.in/I4C pattern: unsolicited DMs from self-styled trading 'gurus' on social media.",
    ),
    ScamQuote(
        "I noticed you're interested in stocks, I can guide you one-on-one if you're serious about profits.",
        "social_media_guru_dm",
        "Unsolicited personal-mentorship DM opener.",
    ),
    ScamQuote(
        "I don't usually do this, but I'll personally help you turn your savings into real wealth.",
        "social_media_guru_dm",
        "False-exclusivity personal-mentorship pitch.",
    ),
    ScamQuote(
        "Saw you follow trading pages, I run a small private group that's outperforming everyone else.",
        "social_media_guru_dm",
        "Social-media targeting based on inferred trading interest.",
    ),
    # --- fake_trading_course ---
    ScamQuote(
        "Join our free trading masterclass this weekend, seats are limited so register now.",
        "fake_trading_course",
        "SEBI PR 27/2025: 'Free Trading Courses' used as a funnel into paid signal groups.",
    ),
    ScamQuote(
        "Learn our winning strategy in this free 3-day course, then unlock the premium signals group.",
        "fake_trading_course",
        "Free-course-to-paid-signals funnel pattern.",
    ),
    ScamQuote(
        "Attend our zero-cost webinar on options trading and get exclusive access to our tips channel.",
        "fake_trading_course",
        "Free-webinar recruitment funnel.",
    ),
    ScamQuote(
        "Complete this free trading bootcamp and graduate straight into our VIP trading circle.",
        "fake_trading_course",
        "Course-completion funnel into a paid recruitment group.",
    ),
    # --- private_link_app_install ---
    ScamQuote(
        "Download our trading app using this private link, it's not on the Play Store yet for early members.",
        "private_link_app_install",
        "I4C advisory: never download trading apps through private links outside official app stores.",
    ),
    ScamQuote(
        "Install this APK directly from the link below to access our exclusive trading dashboard.",
        "private_link_app_install",
        "Sideloaded-APK install pattern outside official app stores.",
    ),
    ScamQuote(
        "This app isn't public yet, use the invite link we sent to install it before everyone else.",
        "private_link_app_install",
        "False-exclusivity framing for a sideloaded app install.",
    ),
    ScamQuote(
        "Click this link to install the members-only version of our trading platform.",
        "private_link_app_install",
        "Members-only app install via untrusted link.",
    ),
    # --- task_scam_bait ---
    ScamQuote(
        "Part time work from home, earn ₹3,000 to ₹15,000 daily, just a few minutes of simple tasks.",
        "task_scam_bait",
        "cybercrime.gov.in/I4C top-reported category: task-based investment fraud initial bait message.",
    ),
    ScamQuote(
        "Easy online job available, rate a few YouTube videos and earn same-day payment.",
        "task_scam_bait",
        "Task-scam bait citing simple video-rating micro-tasks.",
    ),
    ScamQuote(
        "No experience needed, like a few Instagram posts daily and get paid instantly.",
        "task_scam_bait",
        "Task-scam bait citing simple social-media micro-tasks.",
    ),
    ScamQuote(
        "Looking for students and homemakers for a flexible part-time task job, daily payout guaranteed.",
        "task_scam_bait",
        "Task-scam targeting demographic pattern (students/homemakers) noted in I4C advisories.",
    ),
    # --- task_scam_trust_building ---
    ScamQuote(
        "Here's your ₹200 for today's 3 tasks, payment sent instantly to build your trust with us.",
        "task_scam_trust_building",
        "Trust-building stage: scammers pay real small amounts before introducing an 'investment task'.",
    ),
    ScamQuote(
        "Great job on your first task! You've been added to our advanced earners group for bigger tasks.",
        "task_scam_trust_building",
        "Escalation into a secondary group after initial small payouts.",
    ),
    ScamQuote(
        "Payment confirmed for your review task, screenshot attached, welcome to level 2.",
        "task_scam_trust_building",
        "Fake payment-confirmation screenshot used to build trust before escalation.",
    ),
    ScamQuote(
        "You've completed 3/3 tasks successfully, moving you to our premium investment task group now.",
        "task_scam_trust_building",
        "Direct transition language from simple tasks to the investment phase.",
    ),
    # --- task_scam_investment_escalation ---
    ScamQuote(
        "Deposit ₹5,000 for this investment task and receive ₹8,000 back within the hour.",
        "task_scam_investment_escalation",
        "I4C pattern: investment-task phase requiring an upfront deposit with a promised larger return.",
    ),
    ScamQuote(
        "To unlock the next task set, please top up your task wallet with ₹10,000 first.",
        "task_scam_investment_escalation",
        "Escalating deposit requirement framed as a 'task wallet' top-up.",
    ),
    ScamQuote(
        "Your last task profit is pending, deposit one more round to release both amounts together.",
        "task_scam_investment_escalation",
        "Compounding-deposit pressure to release previously 'earned' funds.",
    ),
    ScamQuote(
        "This is a premium task requiring ₹25,000 minimum, returns are 60% higher than regular tasks.",
        "task_scam_investment_escalation",
        "Tiered task pricing with escalating deposit and promised returns.",
    ),
    # --- task_scam_fake_earnings_screenshot ---
    ScamQuote(
        "Look at how much Priya earned this week doing the same tasks, screenshot attached.",
        "task_scam_fake_earnings_screenshot",
        "I4C pattern: fabricated screenshots of other members' earnings used to pressure victims.",
    ),
    ScamQuote(
        "Our group members withdrew over ₹2 lakh combined today, see the proof below.",
        "task_scam_fake_earnings_screenshot",
        "Fabricated group-wide withdrawal proof to build social pressure.",
    ),
    ScamQuote(
        "Here's a screenshot of another member's account balance after just one week with us.",
        "task_scam_fake_earnings_screenshot",
        "Fabricated individual balance screenshot for social proof.",
    ),
    ScamQuote(
        "Everyone in the group is posting their profit screenshots today, don't miss out like last time.",
        "task_scam_fake_earnings_screenshot",
        "Fear-of-missing-out pressure using fabricated group screenshots.",
    ),
    # --- fake_trading_app_generic ---
    ScamQuote(
        "Our app shows your portfolio growing every day, log in now to see your latest returns.",
        "fake_trading_app_generic",
        "Fake trading-app dashboard pattern showing fabricated profit growth.",
    ),
    ScamQuote(
        "This trading platform has helped thousands double their money in weeks, download today.",
        "fake_trading_app_generic",
        "Generic fake-app promotional claim.",
    ),
    ScamQuote(
        "Track your daily profits live on our dashboard, most users are already up 200% this month.",
        "fake_trading_app_generic",
        "Fabricated live-dashboard profit claim.",
    ),
    ScamQuote(
        "Sign up on our exclusive trading portal and start seeing gains from your very first trade.",
        "fake_trading_app_generic",
        "Guaranteed-first-trade-gains framing for a fake platform.",
    ),
    # --- fake_app_withdrawal_block ---
    ScamQuote(
        "To withdraw your profit, please first pay a 20% tax clearance fee to unlock the transaction.",
        "fake_app_withdrawal_block",
        "I4C pattern: genuine brokers never ask you to deposit more money to withdraw funds — the scam is exactly this.",
    ),
    ScamQuote(
        "Your withdrawal is on hold, deposit the processing charge shown on screen to release it instantly.",
        "fake_app_withdrawal_block",
        "Withdrawal-hold pattern demanding an additional deposit to 'unlock' funds.",
    ),
    ScamQuote(
        "A one-time account verification fee is required before your first withdrawal can be processed.",
        "fake_app_withdrawal_block",
        "Fake verification-fee gate on withdrawal.",
    ),
    ScamQuote(
        "Your balance is ready, just clear the small maintenance charge to complete the transfer.",
        "fake_app_withdrawal_block",
        "Fake maintenance-charge gate on withdrawal.",
    ),
    # --- fake_broker_website_clone ---
    ScamQuote(
        "Please log in at our updated secure portal to continue trading without interruption.",
        "fake_broker_website_clone",
        "Cloned broker-login-page phishing pattern.",
    ),
    ScamQuote(
        "Your session expired, re-enter your client ID and password here to resume trading.",
        "fake_broker_website_clone",
        "Fake session-expiry prompt on a cloned login page.",
    ),
    ScamQuote(
        "We've migrated to a new trading domain, please re-login with your existing credentials.",
        "fake_broker_website_clone",
        "Fake domain-migration pretext used to redirect to a cloned login page.",
    ),
    ScamQuote(
        "Verify your account on our new secure gateway before markets open tomorrow.",
        "fake_broker_website_clone",
        "Urgency-framed redirect to a cloned broker gateway.",
    ),
    # --- fake_ipo_allotment ---
    ScamQuote(
        "Get exclusive guaranteed IPO allotment for a minimum investment of ₹5 lakh, limited slots.",
        "fake_ipo_allotment",
        "Reported pattern: exclusive IPO WhatsApp groups demanding investment well above the retail cap.",
    ),
    ScamQuote(
        "We can secure your IPO shares before the public listing with an assured 50-60% return in a month.",
        "fake_ipo_allotment",
        "Fake pre-listing IPO allotment with guaranteed return claim.",
    ),
    ScamQuote(
        "Join our IPO allotment group for guaranteed shares in the next big listing, deposit to reserve your quota.",
        "fake_ipo_allotment",
        "Deposit-to-reserve IPO allotment scam pattern.",
    ),
    ScamQuote(
        "Skip the regular IPO application process, our contact guarantees allotment for a service fee.",
        "fake_ipo_allotment",
        "Bypassing-official-process IPO allotment scam pattern.",
    ),
    # --- dabba_trading_recruit ---
    ScamQuote(
        "Trade with us off-exchange with no paperwork and much lower margin requirements.",
        "dabba_trading_recruit",
        "NSE advisory: illegal 'dabba' trading offers no regulatory protection to investors.",
    ),
    ScamQuote(
        "Skip the official exchange, our private book offers better leverage and instant settlement.",
        "dabba_trading_recruit",
        "Off-exchange 'dabba' trading recruitment framing better terms.",
    ),
    ScamQuote(
        "No demat account needed, just deposit with us and trade directly through our private ledger.",
        "dabba_trading_recruit",
        "Illegal off-exchange trading bypassing demat/exchange infrastructure entirely.",
    ),
    ScamQuote(
        "Our unofficial trading desk lets you trade the same stocks without exchange fees or KYC hassle.",
        "dabba_trading_recruit",
        "'No KYC hassle' framing for illegal off-exchange trading.",
    ),
    # --- fake_algo_trading_bot ---
    ScamQuote(
        "Our automated algo bot trades for you 24/7 and has never had a losing month.",
        "fake_algo_trading_bot",
        "Automated 'algo-trading bot' consistent-profit claim.",
    ),
    ScamQuote(
        "Set it and forget it, our trading bot handles everything and profits keep coming in automatically.",
        "fake_algo_trading_bot",
        "No-effort automated-profit framing for a fake trading bot.",
    ),
    ScamQuote(
        "This AI-powered bot analyses the market better than any human and guarantees steady returns.",
        "fake_algo_trading_bot",
        "AI/algo framing used to justify guaranteed-return claims.",
    ),
    ScamQuote(
        "Subscribe to our auto-trading bot license and watch your account grow without lifting a finger.",
        "fake_algo_trading_bot",
        "Subscription-based automated-bot guaranteed-growth claim.",
    ),
    # --- credential_harvest ---
    ScamQuote(
        "Your demat account will be suspended unless you verify your PAN now.",
        "credential_harvest",
        "Account-suspension threat to force credential disclosure.",
    ),
    ScamQuote(
        "Share the OTP you just received so we can confirm your identity.",
        "credential_harvest",
        "Direct OTP-sharing request; legitimate brokers never ask for OTP/PIN unsolicited.",
    ),
    ScamQuote(
        "For security purposes, please confirm your login password and registered mobile number.",
        "credential_harvest",
        "Credential-harvest framed as a routine security check.",
    ),
    ScamQuote(
        "We need your CVV and card PIN to process the refund to your trading wallet.",
        "credential_harvest",
        "Sensitive-credential request disguised as a refund process.",
    ),
    # --- fake_kyc_update_sms ---
    ScamQuote(
        "Your KYC will expire in 24 hours, update immediately via the link below to avoid account freeze.",
        "fake_kyc_update_sms",
        "Reported broker-impersonation pattern: fake KYC-update urgency with account-freeze threat.",
    ),
    ScamQuote(
        "Demat KYC pending, click here now or your account access will be blocked from tomorrow.",
        "fake_kyc_update_sms",
        "Deadline-driven fake KYC-update phishing SMS.",
    ),
    ScamQuote(
        "As per new exchange rules, re-verify your KYC today using the secure link provided.",
        "fake_kyc_update_sms",
        "False-regulation pretext for a KYC-update phishing link.",
    ),
    ScamQuote(
        "Your PAN-Aadhaar-KYC link is incomplete, complete it within 2 hours to keep trading enabled.",
        "fake_kyc_update_sms",
        "Short-deadline fake KYC-linking phishing SMS.",
    ),
    # --- fake_account_freeze_notice ---
    ScamQuote(
        "Your trading account has been frozen due to suspicious activity, click to reactivate immediately.",
        "fake_account_freeze_notice",
        "Fake already-frozen-account notice used to prompt credential re-entry.",
    ),
    ScamQuote(
        "Account access restricted, verify your identity here to lift the suspension today.",
        "fake_account_freeze_notice",
        "Fake suspension-lift phishing pattern.",
    ),
    ScamQuote(
        "Your demat account is temporarily locked, confirm your details to restore full access.",
        "fake_account_freeze_notice",
        "Fake account-lock phishing pattern.",
    ),
    ScamQuote(
        "Unusual login detected, your account will remain blocked until you confirm your credentials.",
        "fake_account_freeze_notice",
        "Fake unusual-login-block phishing pattern.",
    ),
    # --- fake_broker_support_call ---
    ScamQuote(
        "This is broker support, please install this remote-access app so we can fix your account issue.",
        "fake_broker_support_call",
        "Impersonated broker-support call requesting remote-access app installation.",
    ),
    ScamQuote(
        "I'm calling from your trading platform's technical team, share your screen so I can resolve this.",
        "fake_broker_support_call",
        "Screen-sharing request from a fake technical-support caller.",
    ),
    ScamQuote(
        "Our support desk noticed an error in your account, download this app and enter the code I send you.",
        "fake_broker_support_call",
        "Fake support-desk call directing installation of a remote-access tool.",
    ),
    ScamQuote(
        "As your relationship manager, I need one-time access to your account to correct a system glitch.",
        "fake_broker_support_call",
        "Impersonated relationship-manager requesting account access.",
    ),
    # --- digital_arrest_intro ---
    ScamQuote(
        "This is the cybercrime cell, your bank account is linked to a money-laundering case under investigation.",
        "digital_arrest_intro",
        "MHA/I4C digital-arrest pattern: impersonating police/CBI/ED claiming account linked to a criminal case.",
    ),
    ScamQuote(
        "Your Aadhaar has been used in an illegal parcel case, you are required to cooperate with this investigation.",
        "digital_arrest_intro",
        "Digital-arrest opening pretext citing Aadhaar misuse in a criminal case.",
    ),
    ScamQuote(
        "We are from the enforcement directorate, an FIR has been filed against your trading account.",
        "digital_arrest_intro",
        "Impersonated ED official citing a fabricated FIR against the victim's trading account.",
    ),
    ScamQuote(
        "This is a customs department notice, your account is under scrutiny for suspicious international transfers.",
        "digital_arrest_intro",
        "Customs-impersonation opening pretext for a digital-arrest scam.",
    ),
    # --- digital_arrest_video_hold ---
    ScamQuote(
        "Stay on this video call and do not contact anyone until we clear your name from this case.",
        "digital_arrest_video_hold",
        "MHA/I4C digital-arrest pattern: sustained video-call 'custody' with isolation demand.",
    ),
    ScamQuote(
        "You must remain visible on camera at all times during this investigation or a warrant will be issued.",
        "digital_arrest_video_hold",
        "Continuous-visibility threat used to enforce a fake digital arrest.",
    ),
    ScamQuote(
        "Transfer the verification amount now to the safe account or you will be arrested within the hour.",
        "digital_arrest_video_hold",
        "Money-transfer-to-'clear name' demand under threat of arrest.",
    ),
    ScamQuote(
        "Do not disconnect this call, all your funds must be moved to a government verification account for scrutiny.",
        "digital_arrest_video_hold",
        "Fake 'verification account' fund-transfer demand during a digital-arrest call.",
    ),
    # --- fake_courier_customs_lead_in ---
    ScamQuote(
        "Your parcel containing illegal items has been seized at customs, press 9 to speak to an officer.",
        "fake_courier_customs_lead_in",
        "Fake courier/customs notice used as the lead-in to a digital-arrest scam.",
    ),
    ScamQuote(
        "A package under your name was flagged with banned substances, this call will connect you to the cyber cell.",
        "fake_courier_customs_lead_in",
        "Fake seized-package notice escalating into a law-enforcement impersonation call.",
    ),
    ScamQuote(
        "Your courier is on hold pending verification, please stay on the line to avoid legal action.",
        "fake_courier_customs_lead_in",
        "Fake courier-hold notice used to keep the victim on the line for escalation.",
    ),
    ScamQuote(
        "This automated message is regarding a suspicious shipment linked to your Aadhaar number.",
        "fake_courier_customs_lead_in",
        "Automated fake-shipment notice citing Aadhaar to add false legitimacy.",
    ),
    # --- pump_and_dump ---
    ScamQuote(
        "This penny stock is about to explode, insiders are already buying.",
        "pump_and_dump",
        "Pump-and-dump exhortation.",
    ),
    ScamQuote(
        "Buy this stock today, target hit expected tomorrow, book profits before the crowd catches on.",
        "pump_and_dump",
        "Pump-and-dump exhortation with a specific short timeline.",
    ),
    ScamQuote(
        "Everyone in the group is loading up on this scrip before the price target hits, don't be late.",
        "pump_and_dump",
        "Group-coordinated pump-and-dump urgency framing.",
    ),
    ScamQuote(
        "This small-cap is being accumulated quietly, get in now before the breakout news drops.",
        "pump_and_dump",
        "Pre-breakout accumulation framing typical of pump-and-dump calls.",
    ),
    # --- coordinated_telegram_manipulation ---
    ScamQuote(
        "Everyone buy this stock at 10am sharp, we all exit together at the target price.",
        "coordinated_telegram_manipulation",
        "SEBI enforcement pattern: Telegram channel coordinating simultaneous buying/selling for price manipulation.",
    ),
    ScamQuote(
        "Admin says hold your positions until the signal to sell together is given in the group.",
        "coordinated_telegram_manipulation",
        "Coordinated group sell-signal manipulation pattern.",
    ),
    ScamQuote(
        "Group members are instructed to buy in the next 10 minutes to move the price before the announcement.",
        "coordinated_telegram_manipulation",
        "Time-boxed coordinated-buying manipulation instruction.",
    ),
    ScamQuote(
        "Do not sell until admin gives the word, we need the price to hit target together first.",
        "coordinated_telegram_manipulation",
        "Coordinated sell-timing control by a group admin.",
    ),
    # --- penny_stock_hot_tip ---
    ScamQuote(
        "Unknown small-cap set to multiply 5x this quarter, get in before institutions notice.",
        "penny_stock_hot_tip",
        "Unsolicited hot-tip pattern on an illiquid penny/small-cap stock.",
    ),
    ScamQuote(
        "This microcap scrip is trading under the radar, huge upside expected any day now.",
        "penny_stock_hot_tip",
        "Illiquid microcap hot-tip framing.",
    ),
    ScamQuote(
        "Nobody is talking about this stock yet, but it could multiply several times over in weeks.",
        "penny_stock_hot_tip",
        "Under-the-radar penny-stock multi-fold movement claim.",
    ),
    ScamQuote(
        "Grab this low-priced stock now, we expect it to run up sharply once the news breaks.",
        "penny_stock_hot_tip",
        "Low-priced-stock imminent-movement hot tip.",
    ),
    # --- crypto_scheme ---
    ScamQuote(
        "Convert your savings into a daily-payout crypto plan, withdraw profits every day.",
        "crypto_scheme",
        "Daily-payout crypto scheme pattern.",
    ),
    ScamQuote(
        "Stake your crypto with our platform and earn a fixed 2% daily return, guaranteed.",
        "crypto_scheme",
        "Fixed-daily-return crypto staking scheme pattern.",
    ),
    ScamQuote(
        "Our forex-crypto hybrid fund has never posted a losing week since launch.",
        "crypto_scheme",
        "Never-losing-week crypto/forex fund claim.",
    ),
    ScamQuote(
        "Deposit crypto into our smart contract and watch it grow automatically, no risk involved.",
        "crypto_scheme",
        "No-risk automated crypto-growth scheme pattern.",
    ),
    # --- crypto_pig_butchering ---
    ScamQuote(
        "It's been so nice getting to know you these past weeks, I want to help you grow your savings too.",
        "crypto_pig_butchering",
        "'Pig-butchering' pattern: long online relationship built before introducing a fraudulent investment platform.",
    ),
    ScamQuote(
        "I've been trading on this platform my cousin showed me, I've made great profits, you should try it too.",
        "crypto_pig_butchering",
        "Personal-relationship trust framing used to introduce a fraudulent crypto platform.",
    ),
    ScamQuote(
        "Since we've become close friends, let me show you the app that's been growing my portfolio.",
        "crypto_pig_butchering",
        "Friendship/romance framing preceding a fraudulent crypto platform introduction.",
    ),
    ScamQuote(
        "I only trust you with this, my private platform access has made me a lot of money quietly.",
        "crypto_pig_butchering",
        "False-exclusivity trust appeal within a long-groomed relationship scam.",
    ),
    # --- forex_signal_seller ---
    ScamQuote(
        "Our forex signals have a 98% win rate, subscribe today and never lose a trade again.",
        "forex_signal_seller",
        "Paid forex/binary-options 'signals' claiming a near-100% win rate.",
    ),
    ScamQuote(
        "Join our binary options signal service, our track record shows almost no losing trades.",
        "forex_signal_seller",
        "Binary-options signal-seller near-perfect win-rate claim.",
    ),
    ScamQuote(
        "Get our premium forex alerts and copy our trades exactly for guaranteed pip gains daily.",
        "forex_signal_seller",
        "Copy-trading forex-alert guaranteed-gains claim.",
    ),
    ScamQuote(
        "Our signal bot calls entries and exits with near-perfect accuracy, proven over 3 years.",
        "forex_signal_seller",
        "Automated signal-bot near-perfect-accuracy claim.",
    ),
]

# Keyword -> weight additions derived from the quote bank above, folded into
# phishing_rules.RISKY_KEYWORDS. Weights follow the same 0..1 convention.
KEYWORD_ADDITIONS: dict[str, float] = {
    "risk-free money": 0.5,
    "no-loss": 0.45,
    "consistent payouts": 0.35,
    "double your capital": 0.5,
    "insider tip": 0.45,
    "sure-shot": 0.4,
    "daily-payout": 0.4,
    "vip telegram": 0.35,
    "government-backed wealth scheme": 0.45,
    "account handling": 0.4,
    "highly complex investing technique": 0.35,
    "sebi registration number": 0.3,
    "digitally arrest": 0.6,
    "digital arrest": 0.6,
    "video call custody": 0.55,
    "task wallet": 0.5,
    "investment task": 0.45,
    "dabba trading": 0.5,
    "unlock your withdrawal": 0.5,
    "processing charge": 0.35,
    "tax clearance fee": 0.5,
    "remote-access app": 0.45,
    "screen-sharing": 0.35,
    "assured allotment": 0.45,
    "guaranteed allotment": 0.5,
    "near-certain returns": 0.45,
}
