# FIGURE5_EXTERNAL_RENDER_PACKAGE

This report is a complete, self-contained evidence package for externally recreating the final canonical manuscript Figure 5 without repository access. It does not regenerate the figure, modify manuscript files, or alter any experiment outputs.

## 1. Complete source-file contents

### 1.1 `final_baseline_comparison.csv` (entire file, verbatim content)

```csv
scope,method,n_queries,mean_ndcg,median_ndcg,ci95_low,ci95_high,win_vs_prior,tie_vs_prior,loss_vs_prior,win_vs_best_fixed,tie_vs_best_fixed,loss_vs_best_fixed,runtime_seconds,peak_memory_mb
pooled,prior_only,1020,0.45706728225967597,0.40039596740174466,0.4333376022377195,0.481652483982712,0,1020,0,0,686,334,,
pooled,borda,1020,0.4392788096989783,0.38685280723454163,0.415469268644863,0.46317369614064363,154,553,313,0,609,411,,
pooled,rrf,1020,0.4586538467987258,0.4028934785345258,0.43445194703154644,0.48314037335887094,166,767,87,0,729,291,,
pooled,combsum,1020,0.4621594872777186,0.4082307968370143,0.4383339302574026,0.4868062668845542,219,611,190,0,686,334,,
pooled,score_sum,1020,0.4334223497346488,0.3562071871080222,0.409672664377629,0.4573318212199991,142,550,328,0,601,419,,
pooled,copeland_unrepaired,1020,0.43886360495015025,0.38685280723454163,0.41495032286000194,0.46266613448222293,147,562,311,0,593,427,,
pooled,copeland_repaired,1020,0.43873656865313193,0.38685280723454163,0.414737611478183,0.4627780560356796,151,550,319,0,599,421,,
pooled,markov_unrepaired,1020,0.4343730043122498,0.3562071871080222,0.4099997278566628,0.45769462231599245,154,531,335,0,591,429,,
pooled,markov_repaired,1020,0.4350021542198668,0.3562071871080222,0.41108740068117045,0.4583659901676277,155,531,334,0,595,425,,
pooled,balance,1020,0.4343716931214982,0.3562071871080222,0.4106337956273952,0.458440095546622,150,540,330,0,596,424,,
pooled,proposed_hybrid,1020,0.45488621029735227,0.38790545080129796,0.4309015184667664,0.47945289969156957,116,755,149,18,640,362,,
pooled,best_stronger_repair,1020,0.4548617189919198,0.38790545080129796,0.43088448371985033,0.4794369257595952,115,755,150,17,640,363,,
scidocs,prior_only,360,0.35581542340089134,0.3333333333333333,0.323028627851259,0.3862672889845948,0,360,0,0,225,135,,
scidocs,borda,360,0.32868979242325436,0.3155837178296481,0.30043275226027905,0.35682830358681034,58,164,138,0,182,178,,
scidocs,rrf,360,0.35282338478557185,0.3458935518511479,0.3211234644388133,0.382536866588007,89,227,44,0,247,113,,
scidocs,combsum,360,0.3491427386927966,0.3333333333333333,0.3176869814488464,0.38037548977198743,75,194,91,0,204,156,,
scidocs,score_sum,360,0.3179060485663205,0.3010299956639812,0.2890317274843243,0.3454537672546288,48,157,155,0,169,191,,
scidocs,copeland_unrepaired,360,0.32861043849737587,0.31546487678572877,0.29992577408346394,0.3567204431541047,53,168,139,0,178,182,,
scidocs,copeland_repaired,360,0.32598462106515197,0.31546487678572877,0.29837709048433414,0.35409676245502775,54,162,144,0,176,184,,
scidocs,markov_unrepaired,360,0.31890172320544535,0.3011551272123162,0.2891625758352313,0.34633125646382285,53,151,156,0,169,191,,
scidocs,markov_repaired,360,0.3191667537263868,0.3011551272123162,0.2896823825238266,0.34644064327579677,53,151,156,0,171,189,,
scidocs,balance,360,0.31732241993878063,0.3065692347622484,0.28745769002155597,0.34450882121690224,51,152,157,0,167,193,,
scidocs,proposed_hybrid,360,0.34996345945684504,0.3333333333333333,0.3191201475393162,0.37931714698891533,38,256,66,6,201,153,,
scidocs,best_stronger_repair,360,0.3499181999829174,0.3333333333333333,0.3191201475393162,0.37925418974506947,38,255,67,6,201,153,,
scidocs/ms1,prior_only,120,0.35685723104723,0.33375628224765547,0.2978250015936983,0.4126706406751947,0,120,0,0,74,46,,
scidocs/ms1,borda,120,0.32710052784173577,0.32030923980514875,0.2748802764472835,0.3789743849029051,17,53,50,0,58,62,,
scidocs/ms1,rrf,120,0.3537585662920841,0.3458935518511479,0.2980014203534099,0.40720923810007914,30,75,15,0,83,37,,
scidocs/ms1,combsum,120,0.35046719122107495,0.3333333333333333,0.2949151172061479,0.40684495325876036,26,64,30,0,71,49,,
scidocs/ms1,score_sum,120,0.3160234592858496,0.29932855411903353,0.26609652477090245,0.3680378238709171,15,50,55,0,57,63,,
scidocs/ms1,copeland_unrepaired,120,0.327466804179013,0.31546487678572877,0.2742139989750687,0.37851891040098984,16,56,48,0,58,62,,
scidocs/ms1,copeland_repaired,120,0.3195893518823414,0.30824743622485495,0.2681059961521928,0.371582445269452,17,50,53,0,56,64,,
scidocs/ms1,markov_unrepaired,120,0.3169664845098562,0.30824743622485495,0.2669178564995479,0.3672609361942654,18,50,52,0,57,63,,
scidocs/ms1,markov_repaired,120,0.3175061959049595,0.30824743622485495,0.26671310431223305,0.36852721841472413,18,50,52,0,58,62,,
scidocs/ms1,balance,120,0.3165620528592891,0.3008340973089699,0.2657218485337622,0.3677581973437704,17,50,53,0,55,65,,
scidocs/ms1,proposed_hybrid,120,0.34902072892071817,0.3324746853896558,0.2916438550986963,0.4044501563413655,14,77,29,3,65,52,,
scidocs/ms1,best_stronger_repair,120,0.3488849504989354,0.3324746853896558,0.2916438550986963,0.40431437791958275,14,76,30,3,65,52,,
scidocs/ms2,prior_only,120,0.353731808108214,0.3333333333333333,0.2954346147750791,0.4091195350061295,0,120,0,0,75,45,,
scidocs/ms2,borda,120,0.33311766570910506,0.3333333333333333,0.2790984082774043,0.38639603812545315,22,59,39,0,65,55,,
scidocs/ms2,rrf,120,0.35095302177254734,0.3458935518511479,0.29536722877384497,0.40447974024822203,29,77,14,0,81,39,,
scidocs/ms2,combsum,120,0.34649383363623987,0.3333333333333333,0.2907571950521711,0.4016603410546107,23,66,31,0,64,56,,
scidocs/ms2,score_sum,120,0.32133512997971453,0.31546487678572877,0.26959799414871327,0.37345234819896284,18,54,48,0,58,62,,
scidocs/ms2,copeland_unrepaired,120,0.3308977071341015,0.3148972500331507,0.27673863073179666,0.3842793289407771,21,56,43,0,62,58,,
scidocs/ms2,copeland_repaired,120,0.3308977071341015,0.3148972500331507,0.27673863073179666,0.3842793289407771,21,56,43,0,62,58,,
scidocs/ms2,markov_unrepaired,120,0.3190882035770322,0.29809284786067,0.2669798141321636,0.3726918467559949,16,50,54,0,55,65,,
scidocs/ms2,markov_repaired,120,0.3190882035770322,0.29809284786067,0.2669798141321636,0.3726918467559949,16,50,54,0,55,65,,
scidocs/ms2,balance,120,0.3171735426838927,0.3020959928579267,0.26468121815303064,0.369861945698055,16,51,53,0,56,64,,
scidocs/ms2,proposed_hybrid,120,0.350089630137466,0.33375628224765547,0.2934215737435343,0.4054958740722207,11,97,12,1,70,49,,
scidocs/ms2,best_stronger_repair,120,0.350089630137466,0.33375628224765547,0.2934215737435343,0.4054958740722207,11,97,12,1,70,49,,
scidocs/ms1_drop_mutual,prior_only,120,0.35685723104723,0.33375628224765547,0.2978250015936983,0.4126706406751947,0,120,0,0,76,44,,
scidocs/ms1_drop_mutual,borda,120,0.3258511837189223,0.3109471454558982,0.2732478170831792,0.37709684376307184,19,52,49,0,59,61,,
scidocs/ms1_drop_mutual,rrf,120,0.3537585662920841,0.3458935518511479,0.2980014203534099,0.40720923810007914,30,75,15,0,83,37,,
scidocs/ms1_drop_mutual,combsum,120,0.35046719122107495,0.3333333333333333,0.2949151172061479,0.40684495325876036,26,64,30,0,69,51,,
scidocs/ms1_drop_mutual,score_sum,120,0.3163595564333974,0.3010299956639812,0.2660973534361951,0.3673912366701282,15,53,52,0,54,66,,
scidocs/ms1_drop_mutual,copeland_unrepaired,120,0.327466804179013,0.31546487678572877,0.2742139989750687,0.37851891040098984,16,56,48,0,58,62,,
scidocs/ms1_drop_mutual,copeland_repaired,120,0.327466804179013,0.31546487678572877,0.2742139989750687,0.37851891040098984,16,56,48,0,58,62,,
scidocs/ms1_drop_mutual,markov_unrepaired,120,0.3206504815294477,0.3148972500331507,0.26911775477306027,0.37254317090706984,19,51,50,0,57,63,,
scidocs/ms1_drop_mutual,markov_repaired,120,0.32090586169716867,0.3148972500331507,0.26911775477306027,0.37254317090706984,19,51,50,0,58,62,,
scidocs/ms1_drop_mutual,balance,120,0.31823166427316013,0.31546487678572877,0.26769213664339164,0.37007990771910887,18,51,51,0,56,64,,
scidocs/ms1_drop_mutual,proposed_hybrid,120,0.3507800193123508,0.33690003880850716,0.2935274722234437,0.4055694216211852,13,82,25,2,66,52,,
scidocs/ms1_drop_mutual,best_stronger_repair,120,0.3507800193123508,0.33690003880850716,0.2935274722234437,0.4055694216211852,13,82,25,2,66,52,,
fiqa,prior_only,359,0.3015272622463669,0.0,0.2640041524543198,0.3419654271285748,0,359,0,0,273,86,,
fiqa,borda,359,0.2811953815923892,0.0,0.24548199268864,0.3202848076612053,40,236,83,0,249,110,,
fiqa,rrf,359,0.3095172540720122,0.0,0.26977092764432475,0.3497288994243557,43,299,17,0,292,67,,
fiqa,combsum,359,0.30832244227731687,0.0,0.27098042934620664,0.3498273310723854,63,243,53,0,278,81,,
fiqa,score_sum,359,0.27197469338204516,0.0,0.23762746751982514,0.30923067427395523,33,236,90,0,244,115,,
fiqa,copeland_unrepaired,359,0.27976545007979087,0.0,0.2437908327072674,0.31809586239599086,38,240,81,0,243,116,,
fiqa,copeland_repaired,359,0.2787324091951925,0.0,0.24359146692647082,0.31755274884648305,37,235,87,0,246,113,,
fiqa,markov_unrepaired,359,0.2745341937752629,0.0,0.24074096970944112,0.3129152198646978,36,234,89,0,244,115,,
fiqa,markov_repaired,359,0.2747349812362159,0.0,0.2409603079559355,0.31289727715916305,36,234,89,0,244,115,,
fiqa,balance,359,0.2729375948980944,0.0,0.23867357323598992,0.3103501977321899,32,235,92,0,246,113,,
fiqa,proposed_hybrid,359,0.29701942882862953,0.0,0.2605245398959112,0.3362587066735231,28,284,47,3,261,95,,
fiqa,best_stronger_repair,359,0.29698036186698695,0.0,0.2605245398959112,0.3362196397118805,27,284,48,2,261,96,,
fiqa/ms1,prior_only,120,0.3011977378207325,0.0,0.23831172694191535,0.3687828890508416,0,120,0,0,89,31,,
fiqa/ms1,borda,120,0.2822087656331437,0.0,0.22245419296455815,0.34488415331136013,13,79,28,0,82,38,,
fiqa/ms1,rrf,120,0.3094397681279031,0.0,0.24555041122499463,0.37695034457312426,15,99,6,0,95,25,,
fiqa/ms1,combsum,120,0.30883356725784616,0.0,0.2429160320111105,0.37737620187199894,22,80,18,0,94,26,,
fiqa/ms1,score_sum,120,0.26760098262798004,0.0,0.21004057843577187,0.3269308717783525,9,77,34,0,82,38,,
fiqa/ms1,copeland_unrepaired,120,0.27877839564679413,0.0,0.21946192252191238,0.33995272780847,12,81,27,0,80,40,,
fiqa/ms1,copeland_repaired,120,0.2758784971151599,0.0,0.2148907486425479,0.3371489078746601,11,77,32,0,83,37,,
fiqa/ms1,markov_unrepaired,120,0.2680082160021072,0.0,0.20977786257917191,0.32756271502762835,9,77,34,0,80,40,,
fiqa/ms1,markov_repaired,120,0.2686089051561252,0.0,0.2101830820039974,0.3281476701727051,9,77,34,0,80,40,,
fiqa/ms1,balance,120,0.26797301422298125,0.0,0.20981832112109922,0.32736558393919535,8,77,35,0,82,38,,
fiqa/ms1,proposed_hybrid,120,0.29409239378446633,0.0,0.22988909335204358,0.3605586614716048,7,89,24,0,86,34,,
fiqa/ms1,best_stronger_repair,120,0.29409239378446633,0.0,0.22988909335204358,0.3605586614716048,7,89,24,0,86,34,,
fiqa/ms2,prior_only,119,0.3021918493232765,0.0,0.23700724204514412,0.36801967602557134,0,119,0,0,94,25,,
fiqa/ms2,borda,119,0.2841658178483546,0.0,0.22086629696451515,0.34674486070060884,15,79,25,0,86,33,,
fiqa/ms2,rrf,119,0.3096735282450053,0.0,0.24291941220950783,0.37997044913653516,13,101,5,0,101,18,,
fiqa/ms2,combsum,119,0.3072916019804511,0.0,0.2381759440383241,0.37782305471809874,19,83,17,0,89,30,,
fiqa/ms2,score_sum,119,0.282072372328495,0.0,0.21873580276414295,0.34882530230656905,15,81,23,0,83,36,,
fiqa/ms2,copeland_unrepaired,119,0.28175614809591865,0.0,0.2190628168547349,0.3433719509665481,14,78,27,0,84,35,,
fiqa/ms2,copeland_repaired,119,0.28175614809591865,0.0,0.2190628168547349,0.3433719509665481,14,78,27,0,84,35,,
fiqa/ms2,markov_unrepaired,119,0.28098002601221267,0.0,0.21801620661215945,0.3461445078952111,16,78,25,0,85,34,,
fiqa/ms2,markov_repaired,119,0.28098002601221267,0.0,0.21801620661215945,0.3461445078952111,16,78,25,0,85,34,,
fiqa/ms2,balance,119,0.28241950144687716,0.0,0.21872323415869277,0.3483757805168487,16,79,24,0,85,34,,
fiqa/ms2,proposed_hybrid,119,0.2963759820733756,0.0,0.22982653338472722,0.3662154340054834,12,100,7,2,89,28,,
fiqa/ms2,best_stronger_repair,119,0.2963759820733756,0.0,0.22982653338472722,0.3662154340054834,12,100,7,2,89,28,,
fiqa/ms1_drop_mutual,prior_only,120,0.3011977378207325,0.0,0.23831172694191535,0.3687828890508416,0,120,0,0,90,30,,
fiqa/ms1_drop_mutual,borda,120,0.27723631493113576,0.0,0.21824909715826396,0.3393855331980628,12,78,30,0,81,39,,
fiqa/ms1_drop_mutual,rrf,120,0.3094397681279031,0.0,0.24555041122499463,0.37695034457312426,15,99,6,0,96,24,,
fiqa/ms1_drop_mutual,combsum,120,0.30883356725784616,0.0,0.2429160320111105,0.37737620187199894,22,80,18,0,95,25,,
fiqa/ms1_drop_mutual,score_sum,120,0.2663348725142143,0.0,0.2067885310362996,0.3263035028299241,9,78,33,0,79,41,,
fiqa/ms1_drop_mutual,copeland_unrepaired,120,0.27877839564679413,0.0,0.21946192252191238,0.33995272780847,12,81,27,0,79,41,,
fiqa/ms1_drop_mutual,copeland_repaired,120,0.27858778019867175,0.0,0.21926864166932167,0.3395714969122252,12,80,28,0,79,41,,
fiqa/ms1_drop_mutual,markov_unrepaired,120,0.27466805458011,0.0,0.21451934347595694,0.3356789590577521,11,79,30,0,79,41,,
fiqa/ms1_drop_mutual,markov_repaired,120,0.27466805458011,0.0,0.21451934347595694,0.3356789590577521,11,79,30,0,79,41,,
fiqa/ms1_drop_mutual,balance,120,0.26849928491233127,0.0,0.20918042167198508,0.32840085912978834,8,79,33,0,79,41,,
fiqa/ms1_drop_mutual,proposed_hybrid,120,0.3005845485717529,0.0,0.23514483870047498,0.3698395759937167,9,95,16,1,86,33,,
fiqa/ms1_drop_mutual,best_stronger_repair,120,0.30046767324483886,0.0,0.23509003736356598,0.36972270066680274,8,95,17,0,86,34,,
hotpotqa,prior_only,156,0.8750539733760773,1.0,0.8417645979427635,0.9075316668291714,0,156,0,0,124,32,,
hotpotqa,borda,156,0.8759175936347546,1.0,0.8423455684661877,0.9070908937208813,18,116,22,0,123,33,,
hotpotqa,rrf,156,0.864306565396725,1.0,0.8301035758584356,0.8965405952733423,3,144,9,0,121,35,,
hotpotqa,combsum,156,0.8870967217020543,1.0,0.8546156517402549,0.9169551042097256,14,127,15,0,125,31,,
hotpotqa,score_sum,156,0.9021644293126772,1.0,0.8730536645704268,0.92919022031607,27,114,15,0,134,22,,
hotpotqa,copeland_unrepaired,156,0.8706752440690366,1.0,0.8372052475661608,0.9010972876679952,15,117,24,0,121,35,,
hotpotqa,copeland_repaired,156,0.8805523069168762,1.0,0.8471161851330055,0.9096944298088113,19,116,21,0,125,31,,
hotpotqa,markov_unrepaired,156,0.8925796874674339,1.0,0.8603334235379361,0.9227264744811817,27,109,20,0,132,24,,
hotpotqa,markov_repaired,156,0.8954808975383429,1.0,0.8630158034453771,0.9251000432707528,28,109,19,0,134,22,,
hotpotqa,balance,156,0.9017927112395235,1.0,0.8726902101245739,0.9291838318580434,27,113,16,0,135,21,,
hotpotqa,proposed_hybrid,156,0.8832410683177085,1.0,0.8498811816320893,0.9149349990359422,9,139,8,2,125,29,,
hotpotqa,best_stronger_repair,156,0.8832410683177085,1.0,0.8498811816320893,0.9149349990359422,9,139,8,2,125,29,,
hotpotqa/ms1,prior_only,52,0.8791903324364997,1.0,0.828721089889449,0.9298671681647039,0,52,0,0,40,12,,
hotpotqa/ms1,borda,52,0.8903484493177521,1.0,0.8348443880044598,0.9375763953544263,8,37,7,0,41,11,,
hotpotqa/ms1,rrf,52,0.8684429244571474,1.0,0.8141257812316511,0.9203238760851592,1,48,3,0,40,12,,
hotpotqa/ms1,combsum,52,0.892585229311721,1.0,0.8414366732065103,0.9389806377180417,5,42,5,0,41,11,,
hotpotqa/ms1,score_sum,52,0.9092771323229285,1.0,0.8602610733906484,0.9499629696877521,10,37,5,0,44,8,,
hotpotqa/ms1,copeland_unrepaired,52,0.8796459437794097,1.0,0.8236541030055891,0.9291977121986117,6,38,8,0,40,12,,
hotpotqa/ms1,copeland_repaired,52,0.9092771323229285,1.0,0.8602610733906484,0.9499629696877521,10,37,5,0,44,8,,
hotpotqa/ms1,markov_unrepaired,52,0.9092771323229285,1.0,0.8586595469040295,0.9501939095625326,10,36,6,0,44,8,,
hotpotqa/ms1,markov_repaired,52,0.9179807625356561,1.0,0.8713612359249434,0.9560818516851877,11,36,5,0,46,6,,
hotpotqa/ms1,balance,52,0.9092771323229285,1.0,0.8602610733906484,0.9499629696877521,10,37,5,0,44,8,,
hotpotqa/ms1,proposed_hybrid,52,0.8954104227043838,1.0,0.8403622769003622,0.9452651829813864,5,44,3,1,42,9,,
hotpotqa/ms1,best_stronger_repair,52,0.8954104227043838,1.0,0.8403622769003622,0.9452651829813864,5,44,3,1,42,9,,
hotpotqa/ms2,prior_only,52,0.8667812552552322,1.0,0.8032208265624194,0.9276841231591277,0,52,0,0,43,9,,
hotpotqa/ms2,borda,52,0.8535865832776313,1.0,0.7818803631009411,0.9183742563274596,3,41,8,0,42,10,,
hotpotqa/ms2,rrf,52,0.8560338472758799,1.0,0.7924034201256414,0.9195761455823892,1,48,3,0,42,10,,
hotpotqa/ms2,combsum,52,0.8761197064827206,1.0,0.8066951267229707,0.9369437668475378,4,43,5,0,43,9,,
hotpotqa/ms2,score_sum,52,0.8850867875887114,1.0,0.8135842823988249,0.9424533455641503,7,40,5,0,45,7,,
hotpotqa/ms2,copeland_unrepaired,52,0.8527338446482905,1.0,0.7805648364976909,0.9190399928669092,3,41,8,0,42,10,,
hotpotqa/ms2,copeland_repaired,52,0.8527338446482905,1.0,0.7805648364976909,0.9190399928669092,3,41,8,0,42,10,,
hotpotqa/ms2,markov_unrepaired,52,0.8590499175271729,1.0,0.7871575704810619,0.9260360236614308,7,37,8,0,42,10,,
hotpotqa/ms2,markov_repaired,52,0.8590499175271729,1.0,0.7871575704810619,0.9260360236614308,7,37,8,0,42,10,,
hotpotqa/ms2,balance,52,0.8856255580223471,1.0,0.8133170575659563,0.9433314356748124,8,39,5,0,46,6,,
hotpotqa/ms2,proposed_hybrid,52,0.8713855893888146,1.0,0.8031040476019679,0.9319070676658276,3,46,3,1,42,9,,
hotpotqa/ms2,best_stronger_repair,52,0.8713855893888146,1.0,0.8031040476019679,0.9319070676658276,3,46,3,1,42,9,,
hotpotqa/ms1_drop_mutual,prior_only,52,0.8791903324364997,1.0,0.828721089889449,0.9298671681647039,0,52,0,0,41,11,,
hotpotqa/ms1_drop_mutual,borda,52,0.8838177483088804,1.0,0.8330321558416889,0.931424575462256,7,38,7,0,40,12,,
hotpotqa/ms1_drop_mutual,rrf,52,0.8684429244571474,1.0,0.8141257812316511,0.9203238760851592,1,48,3,0,39,13,,
hotpotqa/ms1_drop_mutual,combsum,52,0.892585229311721,1.0,0.8414366732065103,0.9389806377180417,5,42,5,0,41,11,,
hotpotqa/ms1_drop_mutual,score_sum,52,0.9121293680263916,1.0,0.8644474607020621,0.9510344901494846,10,37,5,0,45,7,,
hotpotqa/ms1_drop_mutual,copeland_unrepaired,52,0.8796459437794097,1.0,0.8236541030055891,0.9291977121986117,6,38,8,0,39,13,,
hotpotqa/ms1_drop_mutual,copeland_repaired,52,0.8796459437794097,1.0,0.8236541030055891,0.9291977121986117,6,38,8,0,39,13,,
hotpotqa/ms1_drop_mutual,markov_unrepaired,52,0.9094120125522002,1.0,0.8565355256822984,0.9507455612556938,10,36,6,0,46,6,,
hotpotqa/ms1_drop_mutual,markov_repaired,52,0.9094120125522002,1.0,0.8565355256822984,0.9507455612556938,10,36,6,0,46,6,,
hotpotqa/ms1_drop_mutual,balance,52,0.9104754433732949,1.0,0.860539229257253,0.9508872678118074,9,37,6,0,45,7,,
hotpotqa/ms1_drop_mutual,proposed_hybrid,52,0.8829271928599274,1.0,0.8286605003521559,0.9333539924614749,1,49,2,0,41,11,,
hotpotqa/ms1_drop_mutual,best_stronger_repair,52,0.8829271928599274,1.0,0.8286605003521559,0.9333539924614749,1,49,2,0,41,11,,
bright,prior_only,145,0.6438508171547231,0.8029926799532722,0.5815946911224953,0.7014577570445645,0,145,0,0,64,81,,
bright,borda,145,0.6354743035992886,0.7875017005661906,0.5802837206571512,0.692069386777564,38,37,70,0,55,90,,
bright,rrf,145,0.6542205986079515,0.8772153153380493,0.5919222609820561,0.7137977706739875,31,97,17,0,69,76,,
bright,combsum,145,0.6664582464192346,0.9055559097947128,0.6058268677532938,0.7249206330269743,67,47,31,0,79,66,,
bright,score_sum,145,0.6156417472312727,0.7537588624946477,0.5538230847265342,0.6744569114184485,34,43,68,0,54,91,,
bright,copeland_unrepaired,145,0.6419309278391951,0.810582531061383,0.5863695523968852,0.6986995045787815,41,37,67,0,51,94,,
bright,copeland_repaired,145,0.6394878735354005,0.810582531061383,0.5828433377484551,0.6956449520406401,41,37,67,0,52,93,,
bright,markov_unrepaired,145,0.6238319809261753,0.7741900178546666,0.5658600432675088,0.6805513923912179,38,37,70,0,46,99,,
bright,markov_repaired,145,0.6239812943653921,0.7741900178546666,0.5660639752417264,0.680750439946214,38,37,70,0,46,99,,
bright,balance,145,0.6217848019599008,0.7565030690421024,0.561100457935999,0.6798350340381992,40,40,65,0,48,97,,
bright,proposed_hybrid,145,0.6453897068399628,0.8276313220637075,0.5827465884704879,0.7012735847007138,41,76,28,7,53,85,,
bright,best_stronger_repair,145,0.6454265159317041,0.8276313220637075,0.5827465884704879,0.7013472028841964,41,77,27,7,53,85,,
bright/ms1,prior_only,50,0.6384797171437183,0.7700871371433883,0.5383574224317254,0.7379057709510234,0,50,0,0,20,30,,
bright/ms1,borda,50,0.6320723159331331,0.7143478640014449,0.5339140549303791,0.7244775647028991,13,11,26,0,17,33,,
bright/ms1,rrf,50,0.6535891199376869,0.7884537984642765,0.5551660277370676,0.7515005135003797,12,33,5,0,23,27,,
bright/ms1,combsum,50,0.6659007432294568,0.8127744405101744,0.5704901194798346,0.7629317257982688,26,13,11,0,25,25,,
bright/ms1,score_sum,50,0.5940702217996325,0.698969429748231,0.4991657256735128,0.68924129488058,11,11,28,0,13,37,,
bright/ms1,copeland_unrepaired,50,0.6428977064367162,0.808956700165319,0.5515121703287785,0.7364455602360656,15,10,25,0,15,35,,
bright/ms1,copeland_repaired,50,0.6361493429880631,0.7869709692084799,0.5422815939472236,0.7286275857889786,16,10,24,0,16,34,,
bright/ms1,markov_unrepaired,50,0.6074638003187297,0.7116424869592137,0.5160413443558172,0.6984626132812356,15,10,25,0,13,37,,
bright/ms1,markov_repaired,50,0.6075337757773689,0.7113799140492754,0.5161359723291802,0.698732168646487,15,10,25,0,13,37,,
bright/ms1,balance,50,0.6052578258577076,0.7135639289822799,0.5128277033324489,0.7010167007503044,15,10,25,0,13,37,,
bright/ms1,proposed_hybrid,50,0.6376329909920407,0.7973388282652367,0.5398648208883714,0.7367800872534147,16,21,13,3,14,33,,
bright/ms1,best_stronger_repair,50,0.6377397373580905,0.7973388282652367,0.5399715672544212,0.7367800872534147,16,22,12,3,14,33,,
bright/ms2,prior_only,45,0.6557865949569562,0.9197207891481876,0.5309959790036329,0.7684514972645887,0,45,0,0,24,21,,
bright/ms2,borda,45,0.6428666980010763,0.8710785440003369,0.5127983262194077,0.753042546732707,12,17,16,0,26,19,,
bright/ms2,rrf,45,0.6556238845418727,0.9197207891481876,0.5318670918616177,0.7713770697692829,7,31,7,0,22,23,,
bright/ms2,combsum,45,0.6676971423965183,0.9469024295259745,0.5416733709109908,0.7871658658566776,15,21,9,0,29,16,,
bright/ms2,score_sum,45,0.6573857504762486,0.9134015924715543,0.5276756043384266,0.7689476534964264,11,21,13,0,27,18,,
bright/ms2,copeland_unrepaired,45,0.6397825309558152,0.8780274953810269,0.5115281778319306,0.7472857650440948,11,17,17,0,23,22,,
bright/ms2,copeland_repaired,45,0.6397825309558152,0.8780274953810269,0.5115281778319306,0.7472857650440948,11,17,17,0,23,22,,
bright/ms2,markov_unrepaired,45,0.6464476209666804,0.8772153153380493,0.5206492690121733,0.7562222387661399,8,17,20,0,18,27,,
bright/ms2,markov_repaired,45,0.6464476209666804,0.8772153153380493,0.5206492690121733,0.7562222387661399,8,17,20,0,18,27,,
bright/ms2,balance,45,0.6497453616472004,0.8816358336694213,0.5222599425280551,0.76044441953793,9,20,16,0,20,25,,
bright/ms2,proposed_hybrid,45,0.6574940638248046,0.9197207891481876,0.5308177080130477,0.7723573112011921,9,32,4,1,23,21,,
bright/ms2,best_stronger_repair,45,0.6574940638248046,0.9197207891481876,0.5308177080130477,0.7723573112011921,9,32,4,1,23,21,,
bright/ms1_drop_mutual,prior_only,50,0.6384797171437183,0.7700871371433883,0.5383574224317254,0.7379057709510234,0,50,0,0,20,30,,
bright/ms1_drop_mutual,borda,50,0.6322231363038352,0.7940914464043979,0.5364844393174841,0.7240079242980176,13,9,28,0,12,38,,
bright/ms1_drop_mutual,rrf,50,0.6535891199376869,0.7884537984642765,0.5551660277370676,0.7515005135003797,12,33,5,0,24,26,,
bright/ms1_drop_mutual,combsum,50,0.6659007432294568,0.8127744405101744,0.5704901194798346,0.7629317257982688,26,13,11,0,25,25,,
bright/ms1_drop_mutual,score_sum,50,0.5996436697424348,0.7209231747091239,0.5016005114196169,0.6946580733548194,12,11,27,0,14,36,,
bright/ms1_drop_mutual,copeland_unrepaired,50,0.6428977064367162,0.808956700165319,0.5515121703287785,0.7364455602360656,15,10,25,0,13,37,,
bright/ms1_drop_mutual,copeland_repaired,50,0.6425612124043646,0.808956700165319,0.5514607519563809,0.7363865584422524,14,10,26,0,13,37,,
bright/ms1_drop_mutual,markov_unrepaired,50,0.6198460854971664,0.7515474130288575,0.5262271419802652,0.7119736465464749,15,10,25,0,15,35,,
bright/ms1_drop_mutual,markov_repaired,50,0.6202091190122557,0.7515474130288575,0.5262271419802652,0.7122186256183867,15,10,25,0,15,35,,
bright/ms1_drop_mutual,balance,50,0.6131472743435243,0.742745314768963,0.5174195744177819,0.7078331457445437,16,10,24,0,15,35,,
bright/ms1_drop_mutual,proposed_hybrid,50,0.6422525014015271,0.7682605640501057,0.5455113919954936,0.7413215356740477,16,23,11,3,16,31,,
bright/ms1_drop_mutual,best_stronger_repair,50,0.6422525014015271,0.7682605640501057,0.5455113919954936,0.7413215356740477,16,23,11,3,16,31,,
```

### 1.2 `FIGURE5_SPECIFICATION.md` (entire file, verbatim content)

```md
# Figure 5 Specification

**Prepared:** 2026-07-12
**Scope:** Canonical plotting package for Figure 5 (pooled mean nDCG@$k$ by ranking method). No image generated in this task.

---

## Design decision

**Selected: Option B — pooled baseline comparison**, matching the comparison already reported in `main.tex` Table 6 (`tab:pooled-baseline`), sourced from `experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv` (`scope=pooled`, 12 methods, $n=1{,}020$ query$\times$regime records).

**Why not Option A (canonical per-dataset comparison):** a per-dataset breakdown of the same 12 methods would require four sub-panels (one per dataset) and roughly 4$\times$ the visual real estate for a claim that Table 6's pooled summary already establishes clearly (CombSUM and RRF outperform every graph-based method); a per-dataset figure is better suited to the supplementary material (already planned as SF01 in `FIGURE_SPECIFICATIONS.md`) than to the main-text Figure 5 slot, on page-efficiency grounds.

**Why not Option C (table instead of figure):** Table 6 already exists and reports the exact same numbers. A bar chart adds genuine value here specifically because a sorted, CI-annotated bar chart makes the ranking among 12 methods and the size of the gap between CombSUM/RRF and the graph-repair methods visually immediate in a way a 12-row table does not — this is the clearest single instance in the paper where a figure communicates the finding better than a table alone, which is why Figure 5 was planned in the first place. We keep Table 6 as the numerical source of record and add Figure 5 as its visual complement, consistent with how Figure 4 and Table 5 already coexist for the bootstrap comparison.

---

## Data provenance and integrity notes

- All 12 rows are the `scope=pooled` rows of `final_baseline_comparison.csv`, re-verified against the canonical file in this session (`grep '^pooled,' final_baseline_comparison.csv`) — not carried over from any earlier, possibly stale, extraction.
- **No illustrative or prototype values are used.** The previously existing `fig_mean_ndcg_hybrids.png` asset (see `FIGURE_STATUS_AUDIT.md`) is a real canonical figure but for a *different* comparison (the 4-method vote-suite hybrid family, not this 12-method pooled grid) and is not used as a source for any value in this package.
- Method names are neutral: the pooled-file's own internal label `proposed_hybrid` is renamed **"Repair-based hybrid (RRF, $\alpha=0.3$)"** and `best_stronger_repair` is renamed **"Exact-for-small-components hybrid"** in the plotting CSV, consistent with `main.tex`'s own established neutral terminology (see the footnote already attached to Table 6 explaining the `proposed_hybrid` label is inherited from the data file, not a claim of novelty). Neither method is labeled "ours" anywhere in the plotting package.
- **Regime-duplication handling:** the pooled corpus (`final_baseline_comparison.csv`) is already a single pooled aggregate across all datasets and regimes — there is no regime column to duplicate in this specific comparison (unlike Figure 4's per-regime breakdown). The `regime_or_pool` field is therefore uniformly `"pooled"` for all 12 rows, which is the correct, non-duplicated representation; no additional collapsing was needed here. (The regime-invariance caveat that matters for Figure 4/Table 5 does not apply to this pooled-file comparison, which was already computed once per method over the full corpus, not once per regime.)

## CI values (for the eventual plot's error bars; not part of the required CSV schema, provided here for completeness)

| Method | Mean nDCG | 95% CI |
|---|---|---|
| CombSUM | 0.4622 | $[0.4383, 0.4868]$ |
| Reciprocal rank fusion | 0.4587 | $[0.4345, 0.4831]$ |
| Prior only | 0.4571 | $[0.4333, 0.4817]$ |
| Repair-based hybrid (RRF, $\alpha=0.3$) | 0.4549 | $[0.4309, 0.4795]$ |
| Exact-for-small-components hybrid | 0.4549 | $[0.4309, 0.4794]$ |
| Borda-count fusion | 0.4393 | $[0.4155, 0.4632]$ |
| Copeland unrepaired | 0.4389 | $[0.4150, 0.4627]$ |
| Copeland repaired | 0.4387 | $[0.4147, 0.4628]$ |
| Markov repaired | 0.4350 | $[0.4111, 0.4584]$ |
| Markov unrepaired | 0.4344 | $[0.4100, 0.4577]$ |
| Balance hybrid | 0.4344 | $[0.4106, 0.4584]$ |
| Score-sum (graph) | 0.4334 | $[0.4097, 0.4573]$ |

---

## Axis and layout specification

- **Type:** Horizontal bar chart, sorted descending by mean nDCG (already reflected in `plot_order`).
- **$x$-axis:** Mean nDCG@$k$, with 95% CI whiskers (values above).
- **$y$-axis:** Method name (neutral labels as in the CSV/table above), ordered by `plot_order`.
- **Color:** Group visually by `graph_dependent` (e.g., one color for graph-independent methods: CombSUM, RRF, Prior only, Borda-count; another for graph-dependent methods: the remaining eight) so the central finding — the top three methods are all graph-independent — is visible at a glance without reading labels closely.
- **Annotation:** Optionally bracket the gap between CombSUM (top) and Copeland repaired (a natural point of reference given its role in Figure 4/Table 5), consistent with the gap already called out in Table 6's own caption in `main.tex`.
- **Size:** 1.5-column width (matches Table 6 and Figure 4's sizing conventions already used elsewhere in the manuscript).

## What must not appear in the image

- No method labeled "ours," "proposed," or "our method" (the neutral renamings above must be used verbatim).
- No p-values or significance stars beyond the CI whiskers themselves (consistent with the manuscript's stated preference for percentile CIs over significance stars, §4.5).
- No values from `fig_mean_ndcg_hybrids.png` (the stale 4-method vote-suite asset).
```

### 1.3 `FIGURE5_CAPTION.md` (entire file, verbatim content)

```md
# Figure 5 Caption Draft

**Figure 5.** Pooled mean nDCG@$k$ by ranking method, across 1,020 query$\times$regime records (failure-mining protocol; Section 4.3). Error bars show 95% bootstrap confidence intervals. Methods are grouped by whether their score depends on the preference graph: CombSUM, reciprocal rank fusion, the prior ranking, and Borda-count fusion do not; the remaining eight methods, including both repaired and unrepaired Copeland, Markov, and balance variants and the repair-based hybrid construction, do. CombSUM and reciprocal rank fusion achieve the highest pooled mean nDCG, ahead of every graph-based method evaluated, including the repaired Copeland hybrid and the repair-based hybrid construction. As noted in Section 4.3, the graph-independent methods' pooled sample reflects corpus completeness across regime-labeled records for the same underlying queries rather than independent per-regime observations; this affects the precision of their own confidence intervals, not the validity of the ordering shown, since every method is scored under the same pooled protocol.

**Note for whoever finalizes the image:** this caption is written to match Table 6's existing prose in `main.tex` §6 as closely as possible so the two do not read as duplicated or inconsistent once the figure is inserted — see `REPETITION_AUDIT.md` for the cross-reference rule applied between this figure and its companion table.
```

### 1.4 Current Figure 5 placeholder / intended LaTeX block from `main.tex`

```tex
% TODO(manuscript-authors): Figure 5 (fig_mean_ndcg_hybrids.png) is a
% partial/earlier asset per FIGURE_PLAN.md's own status table ("Partial;
% needs extension") and does not yet reflect the full 12-method pooled grid
% below. Do not regenerate it from that image's illustrative values. Replace
% this placeholder with a bar chart built directly from
% final_baseline_comparison.csv (scope=pooled) before submission.
\begin{figure}[t]
  \centering
  \fbox{\parbox{0.9\linewidth}{\centering\vspace{1.7cm}
    TODO: Figure 5 -- Pooled mean nDCG@$k$ by method (bar chart with 95\% CI)\\
    To be generated from Table~\ref{tab:pooled-baseline} /
    \texttt{final\_baseline\_comparison.csv} (scope=pooled).\\
    The existing \texttt{fig\_mean\_ndcg\_hybrids.png} asset is a partial,
    pre-canonical prototype and must not be used.
    \vspace{1.7cm}}}
  \caption{Pooled mean nDCG@$k$ by ranking method, 1,020 query$\times$regime
    records (placeholder --- see Table~\ref{tab:pooled-baseline} for the
    exact values pending this figure's regeneration).}
  \Description{Placeholder for a sorted horizontal bar chart of pooled mean
    nDCG at cutoff k across twelve ranking methods, with 95 percent
    confidence interval whiskers, to be generated from the pooled
    baseline comparison table.}
  \label{fig:mean-ndcg-hybrids}
\end{figure}
```

### 1.5 Exact current Table 6 LaTeX and caption from `main.tex`

```tex
\begin{table}[t]
  \caption{Pooled mean nDCG@$k$ by method, 1,020 query$\times$regime records
    (failure-mining protocol; Section~\ref{sec:baselines}). Source:
    \texttt{final\_baseline\_comparison.csv} (scope=pooled).}
  \label{tab:pooled-baseline}
  \begin{tabular}{lc}
    \toprule
    Method & Mean nDCG \\
    \midrule
    CombSUM                  & \textbf{0.462} \\
    Reciprocal rank fusion   & 0.459 \\
    Prior only               & 0.457 \\
    Proposed$^{\ast}$ hybrid (repaired balance/Copeland mix) & 0.455 \\
    Best stronger repair (Table~\ref{tab:repair-variants}) & 0.455 \\
    Borda-count fusion       & 0.439 \\
    Copeland, unrepaired     & 0.439 \\
    Copeland, repaired       & 0.439 \\
    Markov, repaired         & 0.435 \\
    Markov, unrepaired       & 0.434 \\
    Balance hybrid           & 0.434 \\
    Score-sum (graph)        & 0.433 \\
    \bottomrule
  \end{tabular}
\end{table}

\noindent$^{\ast}$We use ``proposed hybrid'' only as the pooled-comparison
method label inherited from the underlying data files, referring to the same
repair-based hybrid construction of Eq.~\eqref{eq:hybrid}; we do not
characterize this construction as a novel contribution of this paper (see
Section~\ref{sec:introduction}).
```

### 1.6 Nearby manuscript paragraphs that interpret Table 6 or Figure 5

Lead-in paragraph:

```tex
The comparison above isolates the marginal effect of repair while holding
fusion and extraction fixed. A separate question is whether the resulting
hybrid pipeline is competitive with simple aggregation rules that never
inspect graph structure at all. Table~\ref{tab:pooled-baseline} reports mean
nDCG@$k$ pooled over the 1,020-record failure-mining corpus
(Section~\ref{sec:baselines}) for twelve methods.
```

Interpretation paragraph:

```tex
CombSUM and reciprocal rank fusion --- both graph-independent
(Section~\ref{sec:baselines}) --- achieve the highest and second-highest
pooled mean nDCG, ahead of every graph-based method including the repaired
Copeland hybrid and the repair-based hybrid construction evaluated in this
paper. The prior ranking alone also exceeds repaired Copeland. This is a
direct answer to whether graph repair combined with hybrid fusion is a
better retrieval strategy than substantially simpler alternatives: on this
pooled comparison, it is not. As noted in Section~\ref{sec:baselines},
CombSUM, RRF, Borda-count, and the prior ranking are regime-invariant by
construction, so their pooled $n$ reflects corpus completeness across
regime-labeled rows for the same underlying queries rather than independent
per-regime observations; this affects the precision of their own reported
estimates, not the validity of the ordering above, since every method in
Table~\ref{tab:pooled-baseline} is scored under the same protocol.
```

Introduction and contribution framing excerpt:

```tex
against stronger exact and near-exact repair variants, which improve the
graph-internal structural objective further but do not change the retrieval
conclusion. We do not restrict the comparison to the repaired-versus-unrepaired
pair alone; we additionally evaluate the repaired hybrid rankings against a
broad grid of fixed aggregation baselines, including reciprocal rank fusion
(RRF) and CombSUM, to test whether graph repair is competitive with much simpler
alternatives once retrieval quality, rather than structural consistency, is
the criterion. Because the hybrid rankings we evaluate combine a graph-derived
component with a prior score vector by fusion, we also examine directly whether
that fusion step itself can mask a graph-level change, so that a null retrieval
result is not silently misattributed to repair being unhelpful when it may
instead reflect the fusion weighting absorbing the repair signal. Finally,
where a graph-based diagnostic such as backward-edge weight is computed against
the same relevance judgments used for retrieval evaluation, we flag that
circularity explicitly rather than presenting it as independent corroboration.

Framed this way, the contribution of this paper is diagnostic and curatorial
rather than algorithmic. We do not propose a new ranking algorithm, and we do
not claim that feedback-arc-set repair is a generally superior reranking
strategy; the evidence does not support that claim, and we say so directly.
Instead, we contribute: (1) a systematic, regime-stratified measurement of
preference-graph structural inconsistency across four benchmarks and 1{,}006
query$\times$regime evaluation records (Table~\ref{tab:dataset-stats}); (2) a
bootstrap-quantified account of when feedback-arc-set repair does and does
not change downstream retrieval
quality, including the single regime in which it reliably does; (3) a
six-class failure taxonomy that explains \emph{why} repair is retrieval-inactive,
neutral, or harmful in specific, interpretable terms, rather than reporting
only aggregate null results; (4) a pooled comparison showing that simple,
fixed aggregation baselines are competitive with or superior to repaired
graph-hybrid rankings, which bears directly on whether structural repair is a
good investment relative to simpler alternatives; and (5) the release of a
curated companion benchmark resource, the Consistency-Aware Reranking
```

Conclusion excerpt:

```tex
under the most permissive vote-extraction regime --- shows an effect
distinguishable from noise, and that effect is not explained by cyclicity
severity alone. Strong, simple aggregation baselines that never inspect
graph structure at all, CombSUM and reciprocal rank fusion in particular,
remain competitive with or superior to every graph-based method evaluated,
including repaired hybrids. A six-class manual failure taxonomy indicates
that the typical outcome of applying repair is inactivity or an evaluation-
invisible tail change, that active harm is a small minority of cases, and
```

## 2. Data dictionary

Repository evidence for metric definition comes from `run_final_method_gap_audit.py`:

```python
DATASET_SPECS = {
    "scidocs": {"top_k": 20},
    "fiqa": {"top_k": 20},
    "hotpotqa": {"top_k": 10},
    "bright": {"top_k": 20},
}
BOOTSTRAP_REPS = 1000
...
def _ci_bootstrap(values: list[float], reps: int = BOOTSTRAP_REPS, seed: int = 13) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(reps):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * (reps - 1))]
    hi = means[int(0.975 * (reps - 1))]
    return lo, hi
```

- `scope`
  Meaning: aggregation scope of the row.
  Values seen: `pooled`, a dataset name (`scidocs`, `fiqa`, `hotpotqa`, `bright`), or `dataset/regime` such as `scidocs/ms1`.
  Type: metadata label.
  Larger/smaller better: not applicable.
  Aggregation unit: depends on scope.
  For `pooled`: all available query x regime records across all four datasets.
  For dataset-only scope: all available query x regime records within that dataset.
  For `dataset/regime`: all available query records within that dataset and regime.

- `method`
  Meaning: raw repository method identifier.
  Type: metadata label.
  Larger/smaller better: not applicable.
  Notes: raw identifiers are not all publication-ready; see Section 3 for the display-label mapping.

- `n_queries`
  Meaning: count of values aggregated for that row.
  Type: count.
  Larger/smaller better: not applicable.
  Aggregation unit:
  For `pooled` and dataset-only rows: count of query x regime records with non-missing nDCG for that method.
  For `dataset/regime` rows: count of query records with non-missing nDCG for that method.
  Verified from code: `n_queries` is written as `len(vals)`, where `vals` is the list of per-record method nDCG values in the selected scope.

- `mean_ndcg`
  Meaning: arithmetic mean of per-record `nDCG@k` values for the row's scope.
  Type: point estimate.
  Larger/smaller better: larger is better.
  Metric definition: `nDCG@k`, where `k` is dataset-specific, not globally fixed.
  Verified `k` values: SciDocs 20, FiQA 20, HotpotQA 10, BRIGHT 20.
  Statistical note: this is the statistic whose bootstrap CI is stored in `ci95_low`/`ci95_high`.

- `median_ndcg`
  Meaning: median of per-record `nDCG@k` values for the row's scope.
  Type: point estimate.
  Larger/smaller better: larger is better.
  Aggregation unit: same per-record units as `mean_ndcg`.

- `ci95_low`
  Meaning: lower endpoint of the stored 95 percent confidence interval for `mean_ndcg`.
  Type: bound.
  Larger/smaller better: not independently optimized; higher values imply a higher compatible mean.
  CI type: unpaired, marginal, percentile bootstrap CI over the mean.
  Bootstrap sample count: 1000.
  Random seed: 13.
  Verified from code: simple resampling with replacement of the method's per-record value list inside the chosen scope.
  Not BCa. Not paired. Not a direct method-to-method comparison.

- `ci95_high`
  Meaning: upper endpoint of the stored 95 percent confidence interval for `mean_ndcg`.
  Type: bound.
  Larger/smaller better: not independently optimized.
  CI type: same as `ci95_low`.
  Bootstrap sample count: 1000.
  Random seed: 13.

- `win_vs_prior`
  Meaning: number of per-record comparisons in the row's scope where this method's nDCG is greater than `prior_only`, using tolerance `1e-12`.
  Type: count.
  Larger/smaller better: larger is better relative to `prior_only`.
  Aggregation unit: per record within the selected scope.

- `tie_vs_prior`
  Meaning: number of per-record comparisons where this method's nDCG equals `prior_only` within tolerance `1e-12`.
  Type: count.
  Larger/smaller better: descriptive, not inherently better.

- `loss_vs_prior`
  Meaning: number of per-record comparisons where this method's nDCG is lower than `prior_only`.
  Type: count.
  Larger/smaller better: smaller is better relative to `prior_only`.

- `win_vs_best_fixed`
  Meaning: number of per-record comparisons where this method's nDCG is greater than the within-record maximum over the `fixed_keys` set used by the task-3 script.
  Type: count.
  Larger/smaller better: larger is better relative to that comparator set.
  Important naming caveat: the field name says `best_fixed`, but the code's comparator set is not limited to fixed fusion baselines. It is:
  `prior_only`, `borda`, `rrf`, `combsum`, `score_sum`, `copeland_unrepaired`, `copeland_repaired`, `markov_unrepaired`, `markov_repaired`, and `balance`.
  That means this field is best read as "vs best non-proposed baseline set used in task 3", not literally "vs best fixed fusion baseline."

- `tie_vs_best_fixed`
  Meaning: number of per-record ties against the same `fixed_keys` comparator set.
  Type: count.
  Larger/smaller better: descriptive, not inherently better.

- `loss_vs_best_fixed`
  Meaning: number of per-record losses against the same `fixed_keys` comparator set.
  Type: count.
  Larger/smaller better: smaller is better.

- `runtime_seconds`
  Meaning: placeholder output field for runtime metadata.
  Type: metadata field.
  Larger/smaller better: not applicable.
  Current file status: blank in all 204 data rows.
  Verified from code: task 3 writes this field as `None` for every summary row.

- `peak_memory_mb`
  Meaning: placeholder output field for memory metadata.
  Type: metadata field.
  Larger/smaller better: not applicable.
  Current file status: blank in all 204 data rows.
  Verified from code: task 3 writes this field as `None` for every summary row.

Anything not directly recoverable from repository evidence is marked here:

- Exact effective-independent-sample-size correction for regime-invariant methods: UNVERIFIED. The repository discusses the caveat, but the stored CIs are the straightforward 1000-replicate marginal bootstraps over the observed per-record rows.
- Any BCa, studentized, stratified, or paired bootstrap for direct baseline-to-baseline comparisons: not present in this file and not evidenced elsewhere for Figure 5.

## 3. Row and method validation

### 3.1 Mechanical validation

- Exact number of data rows: 204.
- Exact number of scopes: 17.
- Exact number of unique raw methods: 12.
- Pooled rows: 12.
- Duplicate `(scope, method)` pairs: none.
- Missing values:
  All columns except `runtime_seconds` and `peak_memory_mb` are complete in all 204 data rows.
  `runtime_seconds` is missing in 204 of 204 rows.
  `peak_memory_mb` is missing in 204 of 204 rows.
- CI sanity check:
  All 204 rows satisfy `ci95_low <= mean_ndcg <= ci95_high`.

### 3.2 Complete method list

Raw method identifier list:

1. `prior_only`
2. `borda`
3. `rrf`
4. `combsum`
5. `score_sum`
6. `copeland_unrepaired`
7. `copeland_repaired`
8. `markov_unrepaired`
9. `markov_repaired`
10. `balance`
11. `proposed_hybrid`
12. `best_stronger_repair`

Duplicate methods:

- Across the whole file, each raw method identifier appears once per scope, so each appears 17 times by design.
- Within the pooled slice used for Figure 5, there are no duplicate methods.

### 3.3 Scope and setting interpretation

Rows represent the same method family under different aggregation scopes, and some method identifiers also encode repair state:

- `pooled`: the exact Figure 5 / Table 6 slice.
- Dataset-only rows: valid for supplementary per-dataset baseline breakdowns, not for Figure 5.
- `dataset/regime` rows: valid for supplementary breakdowns, not for Figure 5.
- `copeland_unrepaired` and `copeland_repaired`: same graph-scoring family, different repair state.
- `markov_unrepaired` and `markov_repaired`: same graph-scoring family, different repair state.
- `balance`: not an unrepaired/repaired pair label in this file. Verified from the task-3 script: it maps to `balance_graph_repaired`.
- `proposed_hybrid`: verified from the task-3 script as `hybrid_repaired_copeland_a0p3_minmax`.
- `best_stronger_repair`: populated from task 2 using the selected stronger repair method. Verified from the script and reports as the relabeled `exact_small_greedy_hybrid`.

### 3.4 Mapping table for pooled methods

| Raw CSV method identifier | Proposed display label | Method family | Repair-based or non-repair baseline | Appears in Table 6 | Should appear in Figure 5 | Reason for inclusion or exclusion |
|---|---|---|---|---|---|---|
| `combsum` | `CombSUM` | Fixed score fusion | Non-repair baseline | Yes | Yes | One of the 12 pooled rows; top point estimate; explicitly required by spec |
| `rrf` | `Reciprocal rank fusion` | Fixed rank fusion | Non-repair baseline | Yes | Yes | One of the 12 pooled rows; second point estimate; explicitly required by spec |
| `prior_only` | `Prior only` | Prior-only fusion baseline | Non-repair baseline | Yes | Yes | One of the 12 pooled rows; explicitly required by spec |
| `proposed_hybrid` | `Repair-based hybrid (RRF alpha=0.3)` | Repaired hybrid | Repair-based | Yes | Yes | One of the 12 pooled rows; use neutral label, not `proposed` |
| `best_stronger_repair` | `Exact-for-small-components hybrid` | Stronger-repair hybrid | Repair-based | Yes | Yes | One of the 12 pooled rows; selected stronger repair from task 2 |
| `borda` | `Borda-count fusion` | Fixed rank aggregation | Non-repair baseline | Yes | Yes | One of the 12 pooled rows; explicitly required by spec |
| `copeland_unrepaired` | `Copeland unrepaired` | Graph-based ranking | Non-repair baseline | Yes | Yes | One of the 12 pooled rows; reference graph method |
| `copeland_repaired` | `Copeland repaired` | Graph-based ranking | Repair-based | Yes | Yes | One of the 12 pooled rows; key comparison target in manuscript prose |
| `markov_repaired` | `Markov repaired` | Graph-based ranking | Repair-based | Yes | Yes | One of the 12 pooled rows; explicitly included in the ready-to-plot file |
| `markov_unrepaired` | `Markov unrepaired` | Graph-based ranking | Non-repair baseline | Yes | Yes | One of the 12 pooled rows; explicitly included in the ready-to-plot file |
| `balance` | `Balance hybrid` | Graph-based hybrid | Repair-based | Yes | Yes | One of the 12 pooled rows; verified in code as `balance_graph_repaired` |
| `score_sum` | `Score-sum (graph)` | Graph-dependent score baseline | Non-repair baseline | Yes | Yes | One of the 12 pooled rows; explicitly included in Table 6 and plotting file |

Neutral-label assessment:

- Already publication-ready with only capitalization/spacing normalization: `CombSUM`, `Prior only`, `Reciprocal rank fusion`, `Borda-count fusion`, `Score-sum (graph)`, `Copeland unrepaired`, `Copeland repaired`, `Markov unrepaired`, `Markov repaired`, `Balance hybrid`.
- Not publication-ready as raw repository labels and should be relabeled neutrally in the figure:
  `proposed_hybrid` -> `Repair-based hybrid (RRF alpha=0.3)`
  `best_stronger_repair` -> `Exact-for-small-components hybrid`

No pooled row should be silently excluded.

Rows excluded from Figure 5 are excluded only by scope:

- The other 192 rows are dataset-level or dataset/regime-level summaries.
- Repository evidence is consistent that those rows belong in supplementary per-dataset breakdowns such as SF01, not in the pooled main-text Figure 5.

## 4. Canonical plotting order

Primary ordering evidence:

1. `FIGURE5_SPECIFICATION.md`: "Horizontal bar chart, sorted descending by mean nDCG."
2. `figure5_ready_to_plot.csv`: explicit `plot_order` 1-12.

### 4.1 Raw order in the pooled CSV

1. `prior_only`
2. `borda`
3. `rrf`
4. `combsum`
5. `score_sum`
6. `copeland_unrepaired`
7. `copeland_repaired`
8. `markov_unrepaired`
9. `markov_repaired`
10. `balance`
11. `proposed_hybrid`
12. `best_stronger_repair`

### 4.2 Final recommended display order

This is the canonical order because it matches both the spec and `figure5_ready_to_plot.csv`.

1. `CombSUM`
2. `Reciprocal rank fusion`
3. `Prior only`
4. `Repair-based hybrid (RRF alpha=0.3)`
5. `Exact-for-small-components hybrid`
6. `Borda-count fusion`
7. `Copeland unrepaired`
8. `Copeland repaired`
9. `Markov repaired`
10. `Markov unrepaired`
11. `Balance hybrid`
12. `Score-sum (graph)`

Exact `figure5_ready_to_plot.csv` content:

```csv
dataset,regime_or_pool,method,mean_ndcg,sample_size,graph_dependent,source_file,plot_order
pooled,pooled,CombSUM,0.4621594872777186,1020,No,final_baseline_comparison.csv,1
pooled,pooled,Reciprocal rank fusion,0.4586538467987258,1020,No,final_baseline_comparison.csv,2
pooled,pooled,Prior only,0.45706728225967597,1020,No,final_baseline_comparison.csv,3
pooled,pooled,Repair-based hybrid (RRF alpha=0.3),0.45488621029735227,1020,Yes,final_baseline_comparison.csv,4
pooled,pooled,Exact-for-small-components hybrid,0.4548617189919198,1020,Yes,final_baseline_comparison.csv,5
pooled,pooled,Borda-count fusion,0.4392788096989783,1020,No,final_baseline_comparison.csv,6
pooled,pooled,Copeland unrepaired,0.43886360495015025,1020,Yes,final_baseline_comparison.csv,7
pooled,pooled,Copeland repaired,0.43873656865313193,1020,Yes,final_baseline_comparison.csv,8
pooled,pooled,Markov repaired,0.4350021542198668,1020,Yes,final_baseline_comparison.csv,9
pooled,pooled,Markov unrepaired,0.4343730043122498,1020,Yes,final_baseline_comparison.csv,10
pooled,pooled,Balance hybrid,0.4343716931214982,1020,Yes,final_baseline_comparison.csv,11
pooled,pooled,Score-sum (graph),0.4334223497346488,1020,Yes,final_baseline_comparison.csv,12
```

## 5. Statistical interpretation

All statements in this section are limited to what the repository actually stores.

- Top-performing method by point estimate: `CombSUM`, mean `0.4621594872777186`.
- Second-performing method by point estimate: `Reciprocal rank fusion`, mean `0.4586538467987258`.
- Prior-only method: `Prior only`, mean `0.45706728225967597`.
- Strongest repair-based method by point estimate: `Repair-based hybrid (RRF alpha=0.3)`, mean `0.45488621029735227`.
  `Exact-for-small-components hybrid` is a near-tie at `0.4548617189919198`, lower by `0.00002449130543247`.

Point-estimate differences:

- `CombSUM - Reciprocal rank fusion = 0.0035056404789928`
- `CombSUM - Prior only = 0.00509220501804263`
- `CombSUM - Repair-based hybrid (RRF alpha=0.3) = 0.00727327698036633`
- `Reciprocal rank fusion - Prior only = 0.00158656453904983`
- `Reciprocal rank fusion - Repair-based hybrid (RRF alpha=0.3) = 0.00376763650137352`
- `Prior only - Repair-based hybrid (RRF alpha=0.3) = 0.0021810719623237`

95 percent marginal CI overlap:

- `CombSUM` CI `[0.4383339302574026, 0.4868062668845542]` overlaps `Reciprocal rank fusion` CI `[0.43445194703154644, 0.48314037335887094]`.
- `CombSUM` CI overlaps `Prior only` CI `[0.4333376022377195, 0.481652483982712]`.
- `CombSUM` CI overlaps `Repair-based hybrid (RRF alpha=0.3)` CI `[0.4309015184667664, 0.47945289969156957]`.
- `Reciprocal rank fusion` CI overlaps `Prior only` CI.
- `Reciprocal rank fusion` CI overlaps `Repair-based hybrid (RRF alpha=0.3)` CI.
- `Prior only` CI overlaps `Repair-based hybrid (RRF alpha=0.3)` CI.

Direct statistical-comparison evidence:

- The repository does not contain paired delta confidence intervals or formal hypothesis tests for direct pooled method-to-method comparisons such as `CombSUM` vs `Reciprocal rank fusion` or `CombSUM` vs `Repair-based hybrid (RRF alpha=0.3)`.
- What the repository does contain for this comparison:
  method-wise marginal bootstrap CIs for each pooled mean;
  win/tie/loss counts vs `prior_only`;
  win/tie/loss counts vs the task-3 comparator set labeled `best_fixed`.

Repository warning against overclaiming:

```md
- Statistical reliability of a positive **method** gain requires paired delta CI excluding zero; see task1 repair-delta CIs — pooled mean nDCG CI alone does not establish superiority.
```

Therefore:

- Overlapping marginal CIs cannot support a claim of "no significant difference."
- Non-overlapping marginal CIs, if they had occurred, still would not be the correct paired test for these within-record method comparisons.
- Safe manuscript language is:
  `highest point estimate`
  `lower by point estimate`
  `competitive with`
  `does not show superiority here`
- Unsafe language is:
  `significantly better`
  `not significantly different`
  `statistically tied`
  `error bars prove no difference`

## 6. Figure design requirements

Verified design requirements from repository evidence:

- Chart type: horizontal bar chart.
- Orientation: horizontal.
- Data slice: exactly the 12 `scope=pooled` rows from `final_baseline_comparison.csv`.
- Ordering: descending `mean_ndcg`, using the `figure5_ready_to_plot.csv` order above.
- X-axis label: `Mean nDCG@k`.
  This is the safest verified label because:
  `main.tex` uses `nDCG@$k$`;
  `FIGURE5_SPECIFICATION.md` uses `nDCG@$k$`;
  the task-3 script uses dataset-specific `k` values (20/20/10/20), so a universal `@15` label is not supported by the producing code.
- Y-axis label: method names as tick labels in the canonical order above.
- Mean display: bars, not points.
- Confidence intervals: show 95 percent method-wise bootstrap CI whiskers.
- Internal title: no internal title should be used; the manuscript caption carries the figure title.
- Grouping dimension: whether the method is graph-dependent (`graph_dependent` in `figure5_ready_to_plot.csv`).
- Placement intent from planning docs: `1.5-column`.
- Existing manuscript asset convention: PNG figure files included from `../../../figures/manuscript/...` with `width=0.95\linewidth`.
- Existing manuscript plotting precedent: `build_manuscript_assets.py` saves manuscript PNG assets at `dpi=300` for the main generated plot.

Repository requirements on what must not appear:

- Do not use the old `fig_mean_ndcg_hybrids.png` values.
- Do not label any method as `ours`, `proposed`, or `our method`.
- Do not add p-values or significance stars.

Items that are not explicitly specified by repository evidence and must be treated as UNVERIFIED if strict canonicality is required:

- Exact x-axis limits.
- Exact y-axis title, if any, beyond method tick labels.
- Exact cap size for CI whiskers.
- Exact line width.
- Exact font size.
- Exact legend placement.
- Exact method-label wrapping rule.
- Exact output dimensions in inches.
- Exact PDF/SVG export settings.

Recommended rendering choices when an exact repository specification is missing:

- X-axis limits:
  minimum at or below `0.409672664377629`
  maximum at or above `0.4868062668845542`
  recommended plotting range: `0.40` to `0.49`
- Legend:
  two entries only: `Graph-independent` and `Graph-dependent`
  recommended placement: upper right inside the plotting area if it does not overlap bars; otherwise above the axes
- Visual encodings:
  do not rely on color alone
  use at least two encodings for family grouping, such as fill tone plus hatch or fill tone plus outline style
- Distinguishing repair-based methods from simple baselines:
  the minimal requirement is the graph-dependent grouping
  if additional emphasis is wanted, use a text annotation or hatch pattern for the three repair-based methods (`Balance hybrid`, `Repair-based hybrid (RRF alpha=0.3)`, `Exact-for-small-components hybrid`)
- Grayscale accessibility:
  required
  use distinct fill/outline/hatch combinations that remain separable when printed in grayscale
- Colorblind safety:
  required
  any color use must be redundant with non-color encodings
- Highlighting:
  older planning material suggested highlighting `CombSUM` in green
  do not implement a color-only green highlight
  if `CombSUM` is highlighted, pair that with a heavier outline or text annotation

Recommended filenames for an external renderer:

- PNG: `fig_mean_ndcg_hybrids.png`
- PDF: `fig_mean_ndcg_hybrids.pdf`
- SVG: `fig_mean_ndcg_hybrids.svg`

These filename recommendations are based on the existing manuscript asset stem `fig_mean_ndcg_hybrids`; only the PNG stem is already present in-repository.

## 7. Caption and accessibility text

### 7.1 Final proposed caption

Figure 5. Pooled mean nDCG@k by ranking method across 1,020 query x regime records from the failure-mining evaluation corpus. Error bars show 95 percent bootstrap confidence intervals for each method's pooled mean. Methods are ordered by point estimate and grouped by whether their score depends on the preference graph. CombSUM and reciprocal rank fusion have the two highest pooled mean nDCG point estimates, followed by the prior ranking; all graph-dependent methods are lower by point estimate. The intervals shown are marginal method-wise confidence intervals, not paired tests between methods.

### 7.2 Final proposed `\Description{}`

Horizontal bar chart of pooled mean nDCG@k for twelve ranking methods on 1,020 query x regime records. Methods are sorted from highest to lowest mean: CombSUM, reciprocal rank fusion, Prior only, Repair-based hybrid (RRF alpha equals 0.3), Exact-for-small-components hybrid, Borda-count fusion, Copeland unrepaired, Copeland repaired, Markov repaired, Markov unrepaired, Balance hybrid, and Score-sum (graph). Each bar includes a 95 percent bootstrap confidence interval. The top three point estimates are the graph-independent methods CombSUM, reciprocal rank fusion, and Prior only.

### 7.3 Necessary corrections to the existing caption draft

- Add `by point estimate` or equivalent wording wherever ordering is described, to avoid implying a paired significance result that the repository does not provide.
- Keep `nDCG@k`, not `nDCG@15`.
- If page budget is tight, the long regime-invariance caveat may stay in the body paragraph instead of the caption; the caption above is shorter and still statistically safe.
- Keep the protocol label `failure-mining` so this comparison is not confused with the vote-suite protocol used for other figures and tables.

### 7.4 Wording to avoid

- `significantly outperforms`
- `not significantly different`
- `statistically tied`
- `error bars show no real difference`
- `best method overall` without the qualifier `by point estimate`

## 8. Manuscript-integration details

### 8.1 Recommended final LaTeX figure block

```tex
\begin{figure}[t]
  \centering
  \includegraphics[width=0.95\linewidth]{../../../figures/manuscript/fig_mean_ndcg_hybrids.png}
  \caption{Pooled mean nDCG@$k$ by ranking method across 1,020 query$\times$regime records from the failure-mining evaluation corpus. Error bars show 95\% bootstrap confidence intervals for each method's pooled mean. Methods are ordered by point estimate and grouped by whether their score depends on the preference graph. CombSUM and reciprocal rank fusion have the two highest pooled mean nDCG point estimates, followed by the prior ranking; all graph-dependent methods are lower by point estimate. The intervals shown are marginal method-wise confidence intervals, not paired tests between methods.}
  \Description{Horizontal bar chart of pooled mean nDCG at cutoff k for twelve ranking methods on 1,020 query by regime records. Methods are sorted from highest to lowest mean: CombSUM, reciprocal rank fusion, Prior only, Repair-based hybrid with reciprocal rank fusion alpha equals 0.3, Exact-for-small-components hybrid, Borda-count fusion, Copeland unrepaired, Copeland repaired, Markov repaired, Markov unrepaired, Balance hybrid, and Score-sum graph. Each bar includes a 95 percent bootstrap confidence interval. The top three point estimates are the graph-independent methods CombSUM, reciprocal rank fusion, and Prior only.}
  \label{fig:mean-ndcg-hybrids}
\end{figure}
```

Why this exact block:

- It preserves the existing figure label.
- It matches the manuscript's existing `includegraphics` convention for Figures 2-4.
- It uses `png`, which is the manuscript's current figure-file convention.
- It uses `0.95\linewidth`, which matches Figures 2-4.

Width caveat:

- Planning docs call this a `1.5-column` figure.
- The current manuscript implementation pattern is single-column `figure[t]` with `width=0.95\linewidth`.
- No exact repository-backed LaTeX pattern for a true `1.5-column` ACM float was found.
- The block above is therefore the safest drop-in manuscript-consistent recommendation.

### 8.2 Sentences in the manuscript that should be updated after Figure 5 is inserted

1. Replace the entire current placeholder figure block in `main.tex` with the final block above.

2. This lead-in sentence should gain a figure cross-reference:

```tex
Table~\ref{tab:pooled-baseline} reports mean nDCG@$k$ pooled over the 1,020-record failure-mining corpus (Section~\ref{sec:baselines}) for twelve methods.
```

Recommended update direction:

```tex
Table~\ref{tab:pooled-baseline} and Figure~\ref{fig:mean-ndcg-hybrids} report mean nDCG@$k$ pooled over the 1,020-record failure-mining corpus (Section~\ref{sec:baselines}) for twelve methods.
```

3. This interpretation paragraph should gain a Figure 5 cross-reference in its first sentence or final sentence:

```tex
CombSUM and reciprocal rank fusion --- both graph-independent (Section~\ref{sec:baselines}) --- achieve the highest and second-highest pooled mean nDCG, ahead of every graph-based method including the repaired Copeland hybrid and the repair-based hybrid construction evaluated in this paper.
```

4. This conclusion sentence should gain a Figure 5 citation:

```tex
Strong, simple aggregation baselines that never inspect graph structure at all, CombSUM and reciprocal rank fusion in particular, remain competitive with or superior to every graph-based method evaluated, including repaired hybrids.
```

5. Optional harmonization after figure insertion:
  Table 6 method labels and Figure 5 labels are numerically consistent but not text-identical.
  If full label consistency is desired later, harmonize:
  `Proposed* hybrid (repaired balance/Copeland mix)` with `Repair-based hybrid (RRF alpha=0.3)`
  `Best stronger repair` with `Exact-for-small-components hybrid`
  This is a table-label issue, not a figure-generation issue.

## 9. Provenance and integrity

### 9.1 Producing experiment directory

- Experiment workspace: `experiments/final_method_gap_audit_20260711_221113`
- Task-3 output directory: `experiments/final_method_gap_audit_20260711_221113/task3`
- Primary file: `experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv`

### 9.2 Producing script and recorded run metadata

- Producing script: `experiments/final_method_gap_audit_20260711_221113/run_final_method_gap_audit.py`
- Recorded session name: `final_method_gap_audit`
- Recorded task-3 branch timing from `RUN_MANIFEST.json`:
  started `2026-07-11 22:59:24`
  finished `2026-07-11 22:59:30`
- Recorded canonical input records path:
  `experiments/failure_class_audit_20260711_212157/analysis/canonical_query_records.jsonl`

Exact recorded command:

- UNVERIFIED. `RUN_MANIFEST.json` and the reports record the workspace, script, session, timings, and outputs, but not the exact shell command used to launch the run.

Relevant run-manifest excerpt:

```json
{
  "session_name": "final_method_gap_audit",
  "workspace": "/home/soroush/consistency-aware-llm-rankin/experiments/final_method_gap_audit_20260711_221113",
  "canonical_records": "/home/soroush/consistency-aware-llm-rankin/experiments/failure_class_audit_20260711_212157/analysis/canonical_query_records.jsonl",
  "branches": {
    "task3_baseline_comparison": {
      "started_at": "2026-07-11 22:59:24",
      "status": "completed",
      "finished_at": "2026-07-11 22:59:30"
    }
  }
}
```

### 9.3 Is the CSV described as canonical anywhere?

Yes.

Direct repository inventory evidence:

```csv
final_baseline_comparison,experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv,"Pooled 1020 query×regime baseline grid (prior, CombSUM, RRF, proposed, etc.)",high,main_table,Results;Discussion,high,yes,no,no
```

This is row 49 of `papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv`.

Further canonicality evidence:

- `FIGURE5_SPECIFICATION.md` says all 12 pooled rows were re-verified against the canonical file in-session.
- `TABLE_PLAN.md` and `FIGURE_DATA_MAP.csv` both point to this exact path for the pooled baseline comparison.

### 9.4 Disagreements and reconciliation notes

1. Current manuscript figure number vs older planning docs:
  `main.tex` and `figure5_evidence/` treat this as Figure 5.
  `FIGURE_SPECIFICATIONS.md` and `FIGURE_DATA_MAP.csv` still refer to the slot as `Figure 6` / `F06`.
  For current manuscript integration, Figure 5 is authoritative.

2. Metric label disagreement:
  `FIGURE_SPECIFICATIONS.md` says `nDCG@15`.
  `main.tex`, `FIGURE5_SPECIFICATION.md`, and the producing script support `nDCG@k`.
  Because the producing script uses dataset-specific `k` values (20/20/10/20), `nDCG@k` is the correct figure label.

3. Old asset status wording disagreement:
  `main.tex` placeholder comments and `manuscript/README.md` describe `fig_mean_ndcg_hybrids.png` as a partial or pre-canonical prototype.
  `FIGURE_STATUS_AUDIT.md` refines this and is more precise:
  the asset is a real canonical figure for a different, narrower comparison, not the correct Figure 5 comparison.
  The audit wording should be preferred.

4. Label disagreement between Table 6 and figure-ready files:
  Table 6 uses `Proposed* hybrid (repaired balance/Copeland mix)` and `Best stronger repair`.
  `figure5_ready_to_plot.csv` uses `Repair-based hybrid (RRF alpha=0.3)` and `Exact-for-small-components hybrid`.
  This is a terminology difference, not a numerical disagreement.

5. Old design-note disagreement about highlighting:
  `FIGURE_SPECIFICATIONS.md` suggests highlighting `CombSUM` in green.
  The present package recommends redundant, grayscale-safe encoding instead of a color-only highlight.

### 9.5 Verification of the currently existing Figure 5 asset

Current existing file:

- `figures/manuscript/fig_mean_ndcg_hybrids.png`
- file size: `122402` bytes

Verdict:

- It is not the correct comparison for final manuscript Figure 5.
- It should not be reused as the Figure 5 rendering.

Why:

- `FIGURE_STATUS_AUDIT.md` states that the existing asset is a 2 x 2 per-dataset grid for four vote-suite methods:
  unrepaired Copeland
  repaired Copeland
  unrepaired balance
  repaired balance
- Final Figure 5 instead requires the pooled 12-method baseline comparison from `final_baseline_comparison.csv` with `scope=pooled`.

## 10. Final external-render checklist

- [x] All numerical values are present.
- [x] All confidence intervals are present.
- [x] All raw method labels are present.
- [x] All recommended display labels are present.
- [x] The canonical pooled-only row filter is explicit.
- [x] The plotting order is explicit.
- [x] The repository-backed design specification is captured.
- [x] The caption is provided.
- [x] The accessibility description is provided.
- [x] The final LaTeX integration block is provided.
- [x] Provenance is documented.
- [x] Known caveats and disagreements are documented.

Remaining missing or UNVERIFIED facts:

- Exact axis limits are not repository-specified.
- Exact CI cap size and line width are not repository-specified.
- Exact font size is not repository-specified.
- Exact legend placement is not repository-specified.
- Exact 1.5-column LaTeX implementation is not repository-specified.
- Exact launch command for the producing run is not recorded.

No numerical or method-identity gaps remain for recreating the figure safely from the repository evidence.
