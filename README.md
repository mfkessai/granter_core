# granter

一時的にGCP内のRoleを付与するツール

## 使い方

### コマンドラインで実行

```
$ pipenv run start set
```

実行時に必要な環境変数

| Key | Val | Example |
| --- | --- | ------- |
| CONFIG_YAML_PATH | 許可したいroleなどが書かれたconfig.yml | config.yml |
| GITHUB_ACTOR | Githubを操作した人のアカウント名※1 | shinofara |
| IAM_ACCESS | 付与したいRole | roles/cloudscheduler.jobRunner |
| IAM_TARGET_ACCOUNT | 付与対象アカウント | hoge@example.com |
| IAM_PERIOD | 付与期間（分） | 15 |

※1に関して、弊社ではGithub Actionsでの利用を前提としているため、GITHUB_ACTORを定義しております。

### Github Actionsで実行

[example.yml](example/github-actions.yml)

### 付与可能なRoleについて

現時点では、[config.yml](config.yml)に記述しているRoleのみ許可しています。  
許可リストは書かれているものだけOKという話ではないですので、必要に応じてPRでメンテできればと思います。  

PRを出す際は、下記公式サイトに書かれたRoleを参考に出して下さい。  
https://console.cloud.google.com/iam-admin/roles

### 特定のメンバーは制限なく付与したい場合

[config.yml](config.yml)内のexclude_membersに書かれたメンバーは上記付与可能なRoleについての制限を受けず、GCP内で付与可能な全てのRoleを付与する事が可能となります。

## License

granter-core is released under the Apache 2.0 license. Please see the [LICENSE](LICENSE) file for more information.

