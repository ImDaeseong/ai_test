#include "stdafx.h"
#include "GameInstallSearch.h"
#include "SteamLauncherSearch.h"
#include "EpicLauncherSearch.h"
#include "NetmarbleLauncherSearch.h"

// 전체 설치 탐지 진입점이다.
// 기본 생성자는 CGameInfo를 GameConfig.json으로 초기화한다.
CGameInstallSearch::CGameInstallSearch()
{
    m_GameInfo.LoadFromLocalConfig();
}

// 지원 플랫폼을 순서대로 탐지하여 결과 배열에 추가한다.
// 각 플랫폼 탐지 전에 info를 초기화해 이전 탐지 결과가 섞이지 않게 한다.
void CGameInstallSearch::SearchAll(CGameInstallArray& arrResult)
{
    arrResult.RemoveAll();

    CGameInstallInfo info;
    if (SearchSteam(info))
        arrResult.Add(info);

    info = CGameInstallInfo();
    if (SearchEpic(info))
        arrResult.Add(info);

    info = CGameInstallInfo();
    if (SearchNetmarble(info))
        arrResult.Add(info);
}

// Steam 설치 정보를 탐지한다.
BOOL CGameInstallSearch::SearchSteam(CGameInstallInfo& info)
{
    CSteamLauncherSearch search(m_GameInfo);
    return search.Search(info);
}

// Epic Games 설치 정보를 탐지한다.
BOOL CGameInstallSearch::SearchEpic(CGameInstallInfo& info)
{
    CEpicLauncherSearch search(m_GameInfo);
    return search.Search(info);
}

// Netmarble 설치 정보를 탐지한다.
BOOL CGameInstallSearch::SearchNetmarble(CGameInstallInfo& info)
{
    CNetmarbleLauncherSearch search(m_GameInfo);
    return search.Search(info);
}
