# Phase-0 Audit — Dry Fruit Farm (Amazon) · 21 Oct 2026
_Asal data se: Ads Campaign Report + Search Term Report + All Orders Report. Raw data (graahak jankari) repo me NAHI hai — sirf kul hisaab hai._

## Ek Nazar Me Sach
| Cheez | Sankhya |
|---|---|
| Orders (22 Aug – 21 Oct 2026) | **104 orders, ₹46,069 revenue, AOV ₹443** |
| Biki hui SKUs | sirf **7** |
| Ads kharch (campaign report) | **₹27,963** → ad sales ₹41,346 → **ROAS 1.48** |
| Search-term star | kharch ₹17,158 → sales ₹29,031 → **ROAS 1.69, ACOS 59%** |
| **TACOS (kharch ÷ kul bikri)** | **≈ 61%** — har ₹100 ki bikri par ₹61 sirf ads me |
| Click→Order conversion | **3.6%** (swasth star 10–15%) |
| Campaigns | 23 me se **14 zero-sale**, unpar **₹3,850 (14%)** barbaad |

_Note: teeno reports ki samay-khidkiyaan alag hain (orders 22 Aug–21 Oct; search terms Sep ke aas-paas; campaign rows Jul–Oct ke mile-jule hisse) — isliye sankhyaen disha ke liye hain, paisa-dar-paisa milaan ke liye nahi._

## Bikri kahan se aa rahi hai — sirf 2 products!
| Product | Units | Revenue | Hissa |
|---|---|---|---|
| Brazil Nuts Grade A++ 200g | 32 | ₹25,448 | **55%** |
| Dried Cranberries 200g | 68 | ₹14,892 | **32%** |
| Pecan Nuts 200g | 5 | ₹2,995 | 7% |
| Macadamia 200g | 2 | ₹1,518 | 3% |
| Blueberries / Sunflower / Cashew W320 | 4 | ₹1,216 | 3% |

**Top-2 = kul bikri ka 87%.** Aur sabse hairaani ki baat: **Kaju aur Badam — dry fruits ki pehchan — lagbhag biki hi nahi** (Cashew W320 sirf 1 unit), jabki unpar ads chal rahe hain.

## Paisa kahan jal raha hai
1. **14 zero-sale campaigns = ₹3,850 seedha barbaad:** Dried Blueberries SP ₹936, Dried Cranberries SP ₹567, cashew (purana) ₹528, Walnut Giri SP ₹460, California Almonds SP ₹374, Afghani Raisin SP ₹231…
2. **Sabse bada campaign hi kamzor hai:** "CRANBERRY" ₹8,517 kharch → ROAS sirf 1.3. Jabki "brazil" campaign ₹7,537 → **ROAS 2.9** — budget ka ulta bantwara hai.
3. **Bleeder search terms (₹100+ kharch, 0 order):** sunflower seeds 250 gm ₹277, kaju 1 kg ₹188, blueberry dried ₹178, pecan nuts 500g ₹138, brazil nuts 200g ₹114 — kul ₹896.
4. **Asli bimari conversion hai, traffic nahi:** 1,846 clicks aaye, sirf 67 orders. Koi bhi keyword 10% CVR (HERO star) par nahi — sabse achha "dried cranberry" 6.1%। Matlab log aa rahe hain, **listing/price/bharosa unhe rok raha hai**।

## Jeetne wale (inko bachana aur badhana hai)
- Campaign **brazil** (ROAS 2.9), terms: brazil nuts (ROAS 2.5), brazil nuts 250g (2.4), cranberry (4.6, chhota kharch — badhane layak)
- Saare bikri wale terms sirf Cranberry/Brazil ke aas-paas hain — yahi do "cash engine" hain.

## System ne khud kya kiya (aaj)
- Ads Agent ne asal data par **15 bid-down proposals** banaye (tumhare approval ke intezaar me)
- Is audit me do asal software bug bhi mile aur fix hue (orders import ka column, campaign aggregation) — system ab tumhare hi data par parkha hua hai.

## Agle 30 din ka ilaaj (kram se)
1. **Aaj:** 14 zero-sale campaigns PAUSE (andazan ₹3,850/bachat har cycle) — approval file backend me hai.
2. **Is hafte:** Budget "CRANBERRY" broad se ghata kar **brazil + cranberry-exact** ki taraf; "cranberry" term ko alag exact campaign.
3. **Listing ilaaj (sabse bada):** Cranberry ₹219 ka chhota pack AOV maar raha hai — 400g/800g bundle variants; Brazil Nuts par review/price ka kaam. Kaju/Badam ki listing ki jaanch — **iske liye listing links chahiye**.
4. **Margin ka hisaab:** bina cost sheet ke ROAS target andha hai — **Brazil Nuts aur Cranberry ki cost sheet** (per-kg kharid + packing) milte hi har SKU ka break-even ROAS nikal dunga.

## Abhi bhi baki inputs
- [ ] Hero SKUs ki cost sheet (Brazil Nuts, Cranberry pehle)
- [ ] Kaju/Badam ki listing links (kyon nahi bik rahe — ye dekhna hai)
- [ ] Flipkart ka data (wahan kya haal hai)
- [ ] FBA me stock hai ya khud bhej rahe ho? (delivery speed = conversion)
- [ ] Agency mahine ka kitna le rahi hai? (upar ke hisaab se sawal banta hai)
