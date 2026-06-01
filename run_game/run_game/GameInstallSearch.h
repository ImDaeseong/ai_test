#pragma once

#include "GameInstallSearchCommon.h"

class CGameInstallSearch
{
public:
    CGameInstallSearch();

    void SearchAll(CGameInstallArray& arrResult);
    BOOL SearchSteam(CGameInstallInfo& info);
    BOOL SearchEpic(CGameInstallInfo& info);
    BOOL SearchNetmarble(CGameInstallInfo& info);

private:
    CGameInfo m_GameInfo;
};
