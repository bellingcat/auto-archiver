# Authentication

The Authentication framework for auto-archiver allows you to add login details for various websites in a flexible way, directly from the configuration file.

There are two main use cases for authentication:
* Some websites require some kind of authentication in order to view the content. Examples include Facebook, Telegram etc.
* Some websites use anti-bot systems to block bot-like tools from accessig the website. Adding real login information to auto-archiver can sometimes bypass this.

## The Authentication Config

You can save your authentication information directly inside your orchestration config file, or as a separate file (for security/multi-deploy purposes). Whether storing your settings inside the orchestration file, or as a separate file, the configuration format is the same.

```{code} yaml
authentication:
   # optional file to load authentication information from, for security or multi-system deploy purposes
   load_from_file: path/to/authentication/file.txt
   # optional setting to load cookies from the named browser on the system.
   cookies_from_browser: firefox
   # optional setting to load cookies from a cookies.txt/cookies.jar file. See note below on extracting these
   cookies_file: path/to/cookies.jar

   twitter.com,x.com:
      username: myusername
      password: 123
    
    facebook.com:
       cookie: single_cookie

    othersite.com:
       api_key: 123
       api_secret: 1234

# All available options:
  # - username: str - the username to use for login
  # - password: str - the password to use for login
  # - api_key: str - the API key to use for login
  # - api_secret: str - the API secret to use for login
  # - cookie: str - a cookie string to use for login (specific to this site)
```

### Recommendations for authentication

1. **Store authentication information separately:**
The authentication part of your configuration contains sensitive information. You should make efforts not to share this with others. For extra security, use the `load_from_file` option to keep your authentication settings out of your configuration file, ideally in a different folder.

2. **Don't use your own personal credentials**
Depending on the website you are extracting information from, there may be rules (Terms of Service) that prohibit you from scraping or extracting information using a bot. If you use your own personal account, there's a possibility it might get blocked/disabled. It's recommended to set up a separate, 'throwaway' account. In that way, if it gets blocked you can easily create another one to continue your archiving.


### How to create a cookies.jar or pass cookies directly to auto-archiver

auto-archiver uses yt-dlp's powerful cookies features under the hood. For instructions on how to extract a cookies.jar (or cookies.txt) file directly from your browser, see the FAQ in the [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)

```{note} For developers:

For information on how to access and use authentication settings from within your module, see the `{generic_extractor}` for an example, or view the [`auth_for_site()` function in BaseModule](../autoapi/core/base_module/index.rst)
```