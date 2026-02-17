"""
2025.08.11
- Combine MSs (6 in total)
- 

"""

import os, sys

mysteps = [
    # 0,         # mstransform to extract only G09.83808 and make ".target" and average on time
    # 1,         # concat 6 MSs to make "all.ms"
    # 2,         # baseline statistics
    # 3,         # imaging for looking the spectrum
    # 4,         # uvcontsub
    # 5,         # imaging continuum and making mask
    # 6          # tclean for both continuum + line assuming to use imcontsub
    # 7,         # tclean for CO(10-9) / H2O(2_20-2_11) / HF(1-0)
    8,         # create moment maps
    # 9,         # imcontsub
    # 10,        # tclean for continuum-subtracted spectrum
    # 11,        # tclean for [OIII]88 and [NII]205 (Tadaki-san)
    12,        # create moment maps for [OIII]88 and [NII]205 (Tadaki-san)
]

# common redshift
zspec = 6.024

############################
# Downloaded calibrated data
############################
dir = "./data/calibrated"
dir_image = os.path.join(dir, "cleanmap")

paths = [
    "/home/tsujtaak/atsujita/HATLASJ0900/HF/data/calibrated/uid___A002_X11b9826_X8c16.ms.split.cal",
    "/home/tsujtaak/atsujita/HATLASJ0900/HF/data/calibrated/uid___A002_X11edb41_Xf378.ms.split.cal",
    "/home/tsujtaak/atsujita/HATLASJ0900/HF/data/calibrated/uid___A002_X12277ed_X3882.ms.split.cal",
    "/home/tsujtaak/atsujita/HATLASJ0900/HF/data/calibrated/uid___A002_X122494b_X10cb6.ms.split.cal",
    "/home/tsujtaak/atsujita/HATLASJ0900/HF/data/calibrated/uid___A002_X122494b_X105dd.ms.split.cal",
    "/home/tsujtaak/atsujita/HATLASJ0900/HF/data/calibrated/uid___A002_X122494b_X11309.ms.split.cal"
]

# Common parameters
tbin = 60  # time binning in seconds
robust_mask = 0.0  # robust parameter for creating mask with continuum imaging. This mask is used for line imaging
nsigma_mask = 1.0  # noise threshold for creating mask. This mask is used for line imaging.

############################
# listobs calibrated data --> spwは必要なものだけだが、fieldはキャリブレーション天体も入っていたので取り除く
# mstransformでfieldを指定して、必要な天体のみ抽出する。あと端の数chはおかしいことがあるので、3chずつdropする。また後でcontinuum subtractionをするときに備えてBARYに変換。
############################
thisstep = 0
if thisstep in mysteps:
    
    for p in paths:
        os.system(f"rm -rf {p}_tbin{tbin}s.target")  # 前のが残っているとエラーになる
        mstransform(
            vis=p,
            spw="0:3~3836, 1:3~3836, 2:3~476, 3:3~476", # 端の数chはおかしいことがあるので、3chずつdropする
            outputvis=p+f"_tbin{tbin}s.target",
            field="G09.83808",
            timeaverage=True, # 時間平均を取る
            timebin=f"{tbin}s", 
            datacolumn="data",  # 指定しないとCORRECTED_DATAがないとエラーになる
            regridms=True,  # これなしにoutframeだけ指定してもエラーは出ないが何も変換されないので注意
            outframe="bary",  # BARYに変換
        )

        listobs(
            vis=p+f"_tbin{tbin}s.target",
            listfile=p+f"_tbin{tbin}s.target.listobs",
            overwrite=True
        )

############################
# Combine MSs
############################
thisstep = 1
if thisstep in mysteps:
    concatvis = os.path.join(dir, f"all_tbin{tbin}s.ms")
    if os.path.exists(concatvis):
        os.system(f"rm -r {concatvis}")

    concat_ms = [p+f"_tbin{tbin}s.target" for p in paths]
    concat(
        vis=concat_ms,
        concatvis=concatvis,
        # freqtol='1MHz', # デフォルトのまま分けて扱う
        copypointing=False  # アンテナポインティングの時系列情報、mosaicなどで使う。
    )
    listobs(
        vis=concatvis, 
        listfile=concatvis+".listobs",
        overwrite=True
    )

############################
# Baseline statistics
############################
thisstep = 2
if thisstep in mysteps:
    sys.path.append("/home/tsujtaak/software/analysis_scripts")
    import analysisUtils as au
    from contextlib import redirect_stdout

    output_file = "baseline_stats.txt"
    os.system(f"rm {output_file}")

    # 上のpathsと、全て合わせたall.msのパスを取得
    paths_all = paths + [os.path.join(dir, "all.ms")]
    with open(output_file, "a") as f:
        for path in paths_all:
            with redirect_stdout(f):
                print(f"############# {os.path.basename(path)} ###############")
                au.getBaselineStats(path)
                print()
    
            
############################
# Imaging for looking the spectrum (plotmsだと天体由来の信号かどうか分かりづらいので面倒だがイメージング)
############################
thisstep = 3
if thisstep in mysteps:
    vis = os.path.join(dir, f"all_tbin{tbin}s.ms") # 上でconcatしたMS
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.T1.dirty")
    os.system(f"rm -rf {imagename}*")
    tclean(
        vis=vis,
        imagename=imagename,
        imsize=300,
        cell="0.1arcsec", # 分解能は0.4"なので0.1"で
        specmode="cube",
        spw="0,1,4,5,8,9",
        outframe="bary",
        deconvolver="hogbom",
        weighting="natural",
        restoringbeam="common",
        niter=0,
        threshold=0,
    )
    exportfits(
        imagename=imagename+".image",
        fitsimage=imagename+".image.fits",
        dropdeg=True,
        overwrite=True
    )

    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.T2.dirty")
    os.system(f"rm -rf {imagename}*")
    tclean(
        vis=vis,
        imagename=imagename,
        imsize=300,
        cell="0.1arcsec", # 分解能は0.4"なので0.1"で
        specmode="cube",
        spw="2,3,6,7,10,11",
        outframe="bary",
        deconvolver="hogbom",
        weighting="natural",
        restoringbeam="common",
        niter=0,
        threshold=0,
        parallel=True
    )
    exportfits(
        imagename=imagename+".image",
        fitsimage=imagename+".image.fits",
        dropdeg=True,
        overwrite=True
    )


############################
# uvcontsub
############################
thisstep = 4
if thisstep in mysteps:
    
    # ------- まずはuvcontsubの使い方を正確に把握するためのテスト -------
    # 1つのMSで試す
    # vis = paths[0] + f"_tbin{tbin}s.target"  
    # test = os.path.join(dir, f"test.contsub")
    # os.system(f"rm -rf {test}")

    # uvcontsub( # デフォルトで"DATA" columnを使う仕様になっている
    #     vis=vis,
    #     outputvis=test,
    #     spw="0~3", # output all spws
    #     fitspec="1:163.9GHz~164.1GHz",
    #     # datacolumn="corrected",
    #     fitorder=1,
    # )
    # listobs(
    #     vis=test,
    #     listfile=test+".listobs",
    #     overwrite=True
    # )
    
    # # uvcontsubする前のイメージング
    # imagename = os.path.join(dir_image, f"test_before")
    # os.system(f"rm -rf {imagename}*")
    # tclean( 
    #     vis=vis,
    #     imagename=imagename,
    #     imsize=300,
    #     cell="0.1arcsec", # 分解能は0.4"なので0.1"で
    #     specmode="cube",
    #     spw="1",
    #     outframe="bary",
    #     deconvolver="hogbom",
    #     weighting="natural",
    #     restoringbeam="common",
    #     niter=0,
    #     threshold=0,
    #     parallel=False
    # )

    # # uvcontsubしたMSのイメージング
    # imagename = os.path.join(dir_image, f"test_after")
    # os.system(f"rm -rf {imagename}*")
    # tclean( 
    #     vis=test,
    #     imagename=imagename,
    #     imsize=300,
    #     cell="0.1arcsec", # 分解能は0.4"なので0.1"で
    #     specmode="cube",
    #     spw="1",
    #     outframe="bary",
    #     deconvolver="hogbom",
    #     weighting="natural",
    #     restoringbeam="common",
    #     niter=0,
    #     threshold=0,
    #     parallel=False
    # )
    # ------- テスト終わり -------
    

    # input MS
    vis = os.path.join(dir, f"all_tbin{tbin}s.ms") # 上でconcatしたMS

    # output MS
    # outputvis = os.path.join(dir, f"all_tbin{tbin}s.ms.contsub")
    outputvis_T1 = os.path.join(dir, f"all_tbin{tbin}s.ms.contsub.T1")
    outputvis_T2 = os.path.join(dir, f"all_tbin{tbin}s.ms.contsub.T2")
    
    # Tune-1
    if os.path.exists(outputvis_T1):
        os.system(f"rm -rf {outputvis_T1}")

    # fitspwをここで定義しておく
    spw_groups_1 = [0, 4, 8, 12, 16, 20]  # 161.8~163.5 GHz
    spw_groups_2 = [1, 5, 9, 13, 17, 21]  # 163.7~163.8 & 164.4~165.3 GHz

    part1 = ",".join([f"{spw}:161.8~163.5GHz" for spw in spw_groups_1])
    part2 = ",".join([f"{spw}:163.7~163.8GHz;164.4~165.3GHz" for spw in spw_groups_2])

    fitspw = f"{part1},{part2}"
    
    uvcontsub_old(
        vis=vis, 
        spw="0,1,4,5,8,9,12,13,16,17,20,21",
        fitspw=fitspw,
        # combine="spw", # Tune1は独立にfitできるので、spwごとに分ける必要はない。
        fitorder=1, 
    )

    # 名前が自動的につくので、outputvis_T1に変更
    os.system(f"mv {vis}.contsub {outputvis_T1}")
    listobs(
        vis=outputvis_T1, 
        listfile=outputvis_T1+".listobs",
        overwrite=True
    )

    # Tune-2
    if os.path.exists(outputvis_T2):
        os.system(f"rm -rf {outputvis_T2}")

    # fitspwをここで定義しておく
    spw_groups_1 = [2, 6, 10, 14, 18, 22]  # 174.0~174.7GHz
    spw_groups_2 = [3, 7, 11, 15, 19, 23]  # 175.17~175.21GHz; 175.73~175.76GHz

    part1 = ",".join([f"{spw}:174.0~174.7GHz" for spw in spw_groups_1])
    part2 = ",".join([f"{spw}:175.17~175.21GHz;175.73~175.76GHz" for spw in spw_groups_2])

    fitspw = f"{part1},{part2}"
    
    uvcontsub_old(
        vis=vis, 
        spw="2,3,6,7,10,11,14,15,18,19,22,23", 
        fitspw=fitspw,
        combine="spw", # Tune2は独立にfitできないので、spwを合わせてfit。
        fitorder=1, 
    )

    # 名前が自動的につくので、outputvis_T2に変更
    os.system(f"mv {vis}.contsub {outputvis_T2}")
    listobs(
        vis=outputvis_T2, 
        listfile=outputvis_T2+".listobs",
        overwrite=True
    )


thisstep = 5
if thisstep in mysteps:

    # ---- imaging param ----
    robust = 0.0  # robust parameter for tclean
    cell = "0.15arcsec"  
    imsize = 400  # imsize for tclean
    nsigma = 2.0  # noise threshold for tclean

    # ---- mask param ----
    noisethreshold = 5.0     # default: 5.0
    sidelobethreshold = 2.0  # default: 2.0
    lownoisethreshold = 1.5  # default: 1.5
    minbeamfrac = 0.3        # default: 0.3
    growiterations = 0      # default: 75-100
    negativethreshold = 0.0  # default: 0.0 (cont) / 7.0 (line)
    fastnoise = False        # default: False

    
    # ---- continuumに使用するspwを指定（step4と同じ）----
    spw_groups_1 = [0, 4, 8, 12, 16, 20]  # 161.8~163.5 GHz
    spw_groups_2 = [1, 5, 9, 13, 17, 21]  # 163.7~163.8 & 164.4~165.3 GHz

    part1 = ",".join([f"{spw}:161.8~163.5GHz" for spw in spw_groups_1])
    part2 = ",".join([f"{spw}:163.7~163.8GHz;164.4~165.3GHz" for spw in spw_groups_2])
    spw_T1 = f"{part1},{part2}"

    spw_groups_3 = [2, 6, 10, 14, 18, 22]  # 174.0~174.7GHz
    spw_groups_4 = [3, 7, 11, 15, 19, 23]  # 175.17~175.21GHz; 175.73~175.76GHz

    part3 = ",".join([f"{spw}:174.0~174.7GHz" for spw in spw_groups_3])
    part4 = ",".join([f"{spw}:175.17~175.21GHz;175.73~175.76GHz" for spw in spw_groups_4])
    spw_T2 = f"{part3},{part4}"

    spw = f"{part1},{part2},{part3},{part4}"

    # ---- Tune1 + Tune2 ----
    vis = os.path.join(dir, f"all_tbin{tbin}s.ms") # 上でconcatしたMS
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.cont.rob_{robust}.sgm_{nsigma}")
    # os.system(f"rm -r {imagename}*")

    # tclean(
    #     vis=vis,
    #     imagename=imagename,
    #     imsize=imsize,
    #     cell=cell, 
    #     specmode="mfs",
    #     spw=spw,  # 上で指定したspwを使う
    #     outframe="bary",
    #     deconvolver="multiscale", # mtmfsの方がいい？
    #     scales=[0, 4, 12],
    #     weighting="briggs",
    #     robust=robust,
    #     restoringbeam="common",
    #     niter=10000000,
    #     nsigma=nsigma,
    #     usemask="auto-multithresh",
    #     noisethreshold=noisethreshold,
    #     sidelobethreshold=sidelobethreshold,
    #     lownoisethreshold=lownoisethreshold,
    #     minbeamfrac=minbeamfrac,
    #     growiterations=growiterations,
    #     negativethreshold=negativethreshold,
    #     fastnoise=fastnoise,
    #     pbcor=True
    # )
    
    # exportfits(
    #     imagename=imagename+".image.pbcor",
    #     fitsimage=imagename+".image.pbcor.fits",
    #     dropdeg=True,
    #     overwrite=True
    # )
    # exportfits(
    #     imagename=imagename+".image",
    #     fitsimage=imagename+".image.fits",
    #     dropdeg=True,
    #     overwrite=True
    # )

    # maskもfitsにしておく
    # exportfits(
    #     imagename=imagename+".mask",
    #     fitsimage=imagename+".mask"+".fits",
    #     dropdeg=True,
    #     overwrite=True
    # )


    # ---- Tune1 or Tune2 ----
    # ---- imaging param ----
    robust = 2.0  # robust parameter for tclean
    cell = "0.15arcsec"  
    imsize = 400  # imsize for tclean
    nsigma = 1.0  # noise threshold for tclean

    # mask はTune1 + Tune2のcontinuumで作ったもの(robust=0.0)で固定
    mask = os.path.join(dir_image, f"all_tbin{tbin}s.ms.cont.rob_{robust_mask}.sgm_{nsigma_mask}.mask")

    for i in [1, 2]:
        if i == 1:
            spw = spw_T1
        else:
            spw = spw_T2

        vis = os.path.join(dir, f"all_tbin{tbin}s.ms") # 上でconcatしたMS
        imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.cont.T{i}.rob_{robust}.sgm_{nsigma}")
        os.system(f"rm -r {imagename}*")

        tclean(
            vis=vis,
            imagename=imagename,
            imsize=imsize,
            cell=cell, 
            specmode="mfs",
            spw=spw,  # 上で指定したspwを使う
            outframe="bary",
            deconvolver="multiscale", # mtmfsの方がいい？
            scales=[0, 4, 12],
            weighting="briggs",
            robust=robust,
            restoringbeam="common",
            niter=10000000,
            nsigma=nsigma,
            usemask="user",
            mask=mask,
            pbcor=True
        )
        
        exportfits(
            imagename=imagename+".image.pbcor",
            fitsimage=imagename+".image.pbcor.fits",
            dropdeg=True,
            overwrite=True
        )
        exportfits(
            imagename=imagename+".image",
            fitsimage=imagename+".image.fits",
            dropdeg=True,
            overwrite=True
        )



thisstep = 6
if thisstep in mysteps:

    # Tune-1
    # ---- imaging param ----
    robust = 2.0  # robust parameter for tclean
    cell = "0.15arcsec"  
    imsize = 400  # imsize for tclean
    nsigma = 2.0  # noise threshold for tclean
    width = "25MHz"  # width for tclean

    vis = os.path.join(dir, f"all_tbin{tbin}s.ms") 
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.T1.rob_{robust}.sgm_{nsigma}")
    os.system(f"rm -rf {imagename}*")

    # ---- maskはcontinuumで作ったもの(robust=0.0)で固定 ----
    mask = os.path.join(dir_image, f"all_tbin{tbin}s.ms.cont.rob_{robust_mask}.sgm_{nsigma_mask}.mask")

    tclean(
        vis=vis,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        specmode="cube",
        spw="0,1,4,5,8,9,12,13,16,17,20,21",
        width=width,
        outframe="bary",
        deconvolver="multiscale", # mtmfsの方がいい？
        scales=[0, 4, 12],
        weighting="briggs",
        robust=robust,
        restoringbeam="common",
        niter=10000000,
        nsigma=nsigma,
        usemask="user",
        mask=mask,
        pbcor=True
    )
    exportfits(
        imagename=imagename+".image.pbcor",
        fitsimage=imagename+".image.pbcor.fits",
        dropdeg=True,
        overwrite=True
    )


    # Tune-2
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.T2.rob_{robust}.sgm_{nsigma}")
    os.system(f"rm -rf {imagename}*")

    tclean(
        vis=vis,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        specmode="cube",
        spw="2,3,6,7,10,11,14,15,18,19,22,23",
        width=width,
        outframe="bary",
        deconvolver="multiscale", # mtmfsの方がいい？
        scales=[0, 4, 12],
        weighting="briggs",
        robust=robust,
        restoringbeam="common",
        niter=10000000,
        nsigma=nsigma,
        usemask="user",
        mask=mask,
        pbcor=True
    )
    exportfits(
        imagename=imagename+".image.pbcor",
        fitsimage=imagename+".image.pbcor.fits",
        dropdeg=True,
        overwrite=True
    )


thisstep = 7
if thisstep in mysteps:

    # ------ CO(10-9) -------
    rest_freq = 1151.985452
    obs_freq = rest_freq / (1 + zspec)  

    # ---- imaging param ----
    robust = 2.0  # robust parameter for tclean
    cell = "0.15arcsec"  
    imsize = 400  # imsize for tclean
    nsigma = 2.0  # noise threshold for tclean
    start = "-1025km/s"
    width = "50km/s"
    nchan = 41

    # ---- input vis ----
    vis = os.path.join(dir, f"all_tbin{tbin}s.ms.contsub.T1")  # 上でuvcontsubしたMS
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.contsub.T1.rob_{robust}.sgm_{nsigma}.CO10-9.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}*")

    # ---- maskはcontinuumで作ったもの(robust=0.0)で固定 ----
    mask = os.path.join(dir_image, f"all_tbin{tbin}s.ms.cont.rob_{robust_mask}.sgm_{nsigma_mask}.mask")

    tclean(
        vis=vis,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        specmode="cube",
        spw="",
        nchan=nchan,
        start=start,
        width=width,
        restfreq=f"{obs_freq}GHz",
        outframe="bary",
        deconvolver="multiscale", # mtmfsの方がいい？
        scales=[0, 4, 12],
        weighting="briggs",
        robust=robust,
        restoringbeam="common",
        niter=10000000,
        nsigma=nsigma,
        usemask="user",
        mask=mask,
        pbcor=True
    )
    exportfits(
        imagename=imagename+".image.pbcor",
        fitsimage=imagename+".image.pbcor.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".image",
        fitsimage=imagename+".image.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".pb",
        fitsimage=imagename+".pb.fits",
        dropdeg=True,
        overwrite=True
    )
    print("tclean of CO(10-9) done")


    # ------ H2O(2_20-2_11) -------
    rest_freq = 1228.788719
    obs_freq = rest_freq / (1 + zspec)  

    # ---- input vis ----
    vis = os.path.join(dir, f"all_tbin{tbin}s.ms.contsub.T2")  # 上でuvcontsubしたMS
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.contsub.T2.rob_{robust}.sgm_{nsigma}.H2O220-211.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}*")

    # ---- maskはcontinuumで作ったもの(robust=0.0)で固定 ----
    mask = os.path.join(dir_image, f"all_tbin{tbin}s.ms.cont.rob_{robust_mask}.sgm_{nsigma_mask}.mask")

    tclean(
        vis=vis,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        specmode="cube",
        spw="",
        nchan=nchan,
        start=start,
        width=width,
        restfreq=f"{obs_freq}GHz",
        outframe="bary",
        deconvolver="multiscale", # mtmfsの方がいい？
        scales=[0, 4, 12],
        weighting="briggs",
        robust=robust,
        restoringbeam="common",
        niter=10000000,
        nsigma=nsigma,
        usemask="user",
        mask=mask,
        pbcor=True
    )
    exportfits(
        imagename=imagename+".image.pbcor",
        fitsimage=imagename+".image.pbcor.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".image",
        fitsimage=imagename+".image.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".pb",
        fitsimage=imagename+".pb.fits",
        dropdeg=True,
        overwrite=True
    )
    print("tclean of H2O(2_20-2_11) done")


    # ------ HF(1-0) -------
    rest_freq = 1232.47627
    obs_freq = rest_freq / (1 + zspec)  

    # ---- input vis ----
    vis = os.path.join(dir, f"all_tbin{tbin}s.ms.contsub.T2")  # 上でuvcontsubしたMS
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.contsub.T2.rob_{robust}.sgm_{nsigma}.HF1-0.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}*")

    # ---- maskはcontinuumで作ったもの(robust=0.0)で固定 ----
    mask = os.path.join(dir_image, f"all_tbin{tbin}s.ms.cont.rob_{robust_mask}.sgm_{nsigma_mask}.mask")

    tclean(
        vis=vis,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        specmode="cube",
        spw="",
        nchan=nchan,
        start=start,
        width=width,
        restfreq=f"{obs_freq}GHz",
        outframe="bary",
        deconvolver="multiscale", # mtmfsの方がいい？
        scales=[0, 4, 12],
        weighting="briggs",
        robust=robust,
        restoringbeam="common",
        niter=10000000,
        nsigma=nsigma,
        usemask="user",
        mask=mask,
        pbcor=True
    )
    exportfits(
        imagename=imagename+".image.pbcor",
        fitsimage=imagename+".image.pbcor.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".image",
        fitsimage=imagename+".image.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".pb",
        fitsimage=imagename+".pb.fits",
        dropdeg=True,
        overwrite=True
    )
    print("tclean of HF(1-0) done")


thisstep = 8
if thisstep in mysteps:

    # select file
    robust = 2.0  # robust parameter for tclean
    nsigma = 2.0  # noise threshold for tclean
    width = "50km/s"

    # select channels (H2Oを基準に決めた)
    start_ch = 14  # 15:-250 km/s
    end_ch   = 26  # 25:+250 km/s

    # ---- CO(10-9) ----
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.contsub.T1.rob_{robust}.sgm_{nsigma}.CO10-9.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}.image.mom0")
    os.system(f"rm -rf {imagename}.image.pbcor.mom0")
    
    immoments(
        imagename=imagename+".image.pbcor",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.pbcor.mom0",
    )
    immoments(
        imagename=imagename+".image",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.mom0",
    )
    exportfits(
        imagename=imagename+".image.pbcor.mom0",
        fitsimage=imagename+".image.pbcor.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".image.mom0",
        fitsimage=imagename+".image.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    print("moment0 of CO(10-9) done")

    # ---- H2O(2_20-2_11) ----
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.contsub.T2.rob_{robust}.sgm_{nsigma}.H2O220-211.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}.image.mom0")
    os.system(f"rm -rf {imagename}.image.pbcor.mom0")
    
    immoments(
        imagename=imagename+".image.pbcor",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.pbcor.mom0",
    )
    immoments(
        imagename=imagename+".image",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.mom0",
    )
    exportfits(
        imagename=imagename+".image.pbcor.mom0",
        fitsimage=imagename+".image.pbcor.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".image.mom0",
        fitsimage=imagename+".image.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    print("moment0 of H2O(2_20-2_11) done")

    # ---- HF(1-0) ----
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.contsub.T2.rob_{robust}.sgm_{nsigma}.HF1-0.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}.image.mom0")
    os.system(f"rm -rf {imagename}.image.pbcor.mom0")
    
    immoments(
        imagename=imagename+".image.pbcor",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.pbcor.mom0",
    )
    immoments(
        imagename=imagename+".image",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.mom0",
    )
    exportfits(
        imagename=imagename+".image.pbcor.mom0",
        fitsimage=imagename+".image.pbcor.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".image.mom0",
        fitsimage=imagename+".image.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    print("moment0 of HF(1-0) done")


thisstep = 10
if thisstep in mysteps:

    # Tune-1
    # ---- imaging param ----
    robust = 2.0  # robust parameter for tclean
    cell = "0.15arcsec"  
    imsize = 400  # imsize for tclean
    nsigma = 1.0  # noise threshold for tclean
    width = "25MHz"  # width for tclean

    vis = os.path.join(dir, f"all_tbin{tbin}s.ms.contsub.T1") 
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.contsub.T1.rob_{robust}.sgm_{nsigma}.dv_{width}")
    os.system(f"rm -rf {imagename}*")

    # ---- maskはcontinuumで作ったもの(robust=0.0)で固定 ----
    mask = os.path.join(dir_image, f"all_tbin{tbin}s.ms.cont.rob_{robust_mask}.sgm_{nsigma_mask}.mask")

    tclean(
        vis=vis,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        specmode="cube",
        spw="",
        width=width,
        outframe="bary",
        deconvolver="multiscale", # mtmfsの方がいい？
        scales=[0, 4, 12],
        weighting="briggs",
        robust=robust,
        restoringbeam="common",
        niter=10000000,
        nsigma=nsigma,
        usemask="user",
        mask=mask,
        pbcor=True
    )
    exportfits(
        imagename=imagename+".image.pbcor",
        fitsimage=imagename+".image.pbcor.fits",
        dropdeg=True,
        overwrite=True
    )


    # Tune-2
    vis = os.path.join(dir, f"all_tbin{tbin}s.ms.contsub.T2") 
    imagename = os.path.join(dir_image, f"all_tbin{tbin}s.ms.contsub.T2.rob_{robust}.sgm_{nsigma}.dv_{width}")
    os.system(f"rm -rf {imagename}*")

    tclean(
        vis=vis,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        specmode="cube",
        spw="",
        width=width,
        outframe="bary",
        deconvolver="multiscale", # mtmfsの方がいい？
        scales=[0, 4, 12],
        weighting="briggs",
        robust=robust,
        restoringbeam="common",
        niter=10000000,
        nsigma=nsigma,
        usemask="user",
        mask=mask,
        pbcor=True
    )
    exportfits(
        imagename=imagename+".image.pbcor",
        fitsimage=imagename+".image.pbcor.fits",
        dropdeg=True,
        overwrite=True
    )

thisstep = 11
if thisstep in mysteps:
    # From Tadaki-san parameter
    # ---- imaging param ----
    robust = 2.0  # robust parameter for tclean
    cell = "0.10arcsec"  
    imsize = 300  # imsize for tclean
    nsigma = 2.0  # noise threshold for tclean
    start = "-1025km/s"
    width = "50km/s"
    nchan = 41

    # ------ [OIII]88 -------
    rest_freq = 3393.006244
    obs_freq = rest_freq / (1 + zspec)  

    # ---- input vis ----
    vis = "/home/tsujtaak/atsujita/HATLASJ0900/Tadaki-san/band8/HATLAS_J090045_B8.ms.contsub"
    imagename = os.path.join(dir_image, f"OIII_rob_{robust}.sgm_{nsigma}.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}*")

    # ---- maskはcontinuumで作ったもの(robust=0.0)で固定 ----
    # mask = os.path.join(dir_image, f"all_tbin{tbin}s.ms.cont.rob_{robust_mask}.sgm_{nsigma_mask}.mask")
    # ---- maskはTadaki-san continuumで作ったもの(robust=0.5)で固定 ----
    mask_Tadaki = "/home/tsujtaak/atsujita/HATLASJ0900/Tadaki-san/cleanmap/HATLAS_B5_cont_robust0.5.mask"

    tclean(
        vis=vis,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        specmode="cube",
        spw="",
        nchan=nchan,
        start=start,
        width=width,
        restfreq=f"{obs_freq}GHz",
        outframe="bary",
        deconvolver="multiscale", # mtmfsの方がいい？
        scales=[0, 7, 18],
        weighting="briggs",
        robust=robust,
        restoringbeam="common",
        niter=10000000,
        nsigma=nsigma,
        usemask="user",
        mask=mask_Tadaki,
        pbcor=True
    )
    exportfits(
        imagename=imagename+".image.pbcor",
        fitsimage=imagename+".image.pbcor.fits",
        dropdeg=True,
        overwrite=True
    )
    print("tclean of [OIII]88 done")


    # ------ [NII]205 -------
    rest_freq = 1461.1314062
    obs_freq = rest_freq / (1 + zspec)  

    # ---- input vis ----
    vis = "/home/tsujtaak/atsujita/HATLASJ0900/Tadaki-san/band5_qa2/HATLAS_J090045_B5_NII.ms.contsub"
    imagename = os.path.join(dir_image, f"NII_rob_{robust}.sgm_{nsigma}.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}*")

    tclean(
        vis=vis,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        specmode="cube",
        spw="",
        nchan=nchan,
        start=start,
        width=width,
        restfreq=f"{obs_freq}GHz",
        outframe="bary",
        deconvolver="multiscale", # mtmfsの方がいい？
        scales=[0, 8, 18],
        weighting="briggs",
        robust=robust,
        restoringbeam="common",
        niter=10000000,
        nsigma=nsigma,
        usemask="user",
        mask=mask_Tadaki,
        pbcor=True
    )
    exportfits(
        imagename=imagename+".image.pbcor",
        fitsimage=imagename+".image.pbcor.fits",
        dropdeg=True,
        overwrite=True
    )
    print("tclean of [NII]205 done")


thisstep = 12
if thisstep in mysteps:

    # select file
    robust = 2.0  # robust parameter for tclean
    nsigma = 2.0  # noise threshold for tclean
    width = "50km/s"

    # select channels (H2Oを基準に決めた)
    start_ch = 14  # 15:-250 km/s
    end_ch   = 26  # 25:+250 km/s
    
    # ---- [OIII]88 ----
    imagename = os.path.join(dir_image, f"OIII_rob_{robust}.sgm_{nsigma}.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}.image.mom0")
    os.system(f"rm -rf {imagename}.image.pbcor.mom0")
    
    immoments(
        imagename=imagename+".image.pbcor",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.pbcor.mom0",
    )
    immoments(
        imagename=imagename+".image",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.mom0",
    )
    exportfits(
        imagename=imagename+".image.pbcor.mom0",
        fitsimage=imagename+".image.pbcor.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".image.mom0",
        fitsimage=imagename+".image.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    print("moment0 of [OIII]88 done")


    # ---- [NII]205 ----
    imagename = os.path.join(dir_image, f"NII_rob_{robust}.sgm_{nsigma}.dv_{width.replace('km/s', '')}")
    os.system(f"rm -rf {imagename}.image.mom0")
    os.system(f"rm -rf {imagename}.image.pbcor.mom0")

    immoments(
        imagename=imagename+".image.pbcor",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.pbcor.mom0",
    )
    immoments(
        imagename=imagename+".image",
        moments=[0],
        chans=f"{start_ch}~{end_ch}",
        outfile=imagename+".image.mom0",
    )
    exportfits(
        imagename=imagename+".image.pbcor.mom0",
        fitsimage=imagename+".image.pbcor.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    exportfits(
        imagename=imagename+".image.mom0",
        fitsimage=imagename+".image.mom0.fits",
        dropdeg=True,
        overwrite=True
    )
    print("moment0 of [NII]205 done")